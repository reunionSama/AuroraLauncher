# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import hashlib,json,os,threading,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import urlparse
import requests
from . import USER_AGENT
from .storage import atomic_json,load_json

class Cancelled(Exception):pass
class Net:
    def __init__(self,cache:Path,source="auto",workers=12,cancel=None):
        self.cache=cache;cache.mkdir(parents=True,exist_ok=True);self.source=source;self.workers=workers
        self.cancel=cancel or threading.Event();self.local=threading.local();self._hashes={};self._lock=threading.Lock();self.prefer_mirror=source=="bmclapi"
    def check(self):
        if self.cancel.is_set():raise Cancelled("任务已取消；已下载的文件会保留")
    def session(self):
        if not hasattr(self.local,"s"):
            self.local.s=requests.Session();self.local.s.headers.update({"User-Agent":USER_AGENT})
            adapter=requests.adapters.HTTPAdapter(pool_connections=16,pool_maxsize=16)
            self.local.s.mount("https://",adapter);self.local.s.mount("http://",adapter)
        return self.local.s
    def urls(self,url):
        p=urlparse(url);host=p.netloc
        mirror=None
        if host in ("piston-meta.mojang.com","launchermeta.mojang.com"):mirror="https://bmclapi2.bangbang93.com"+p.path
        elif host in ("piston-data.mojang.com","launcher.mojang.com"):mirror="https://bmclapi2.bangbang93.com"+p.path
        elif host=="resources.download.minecraft.net":mirror="https://bmclapi2.bangbang93.com/assets"+p.path
        elif host=="libraries.minecraft.net":mirror="https://bmclapi2.bangbang93.com/maven"+p.path
        if not mirror:return [url]
        ordered=[mirror,url] if self.prefer_mirror else [url,mirror]
        if host=="piston-data.mojang.com":ordered.append("https://launcher.mojang.com"+p.path)
        return ordered
    def json(self,urls,key="",ttl=0,limit=4*1024*1024):
        urls=[urls] if isinstance(urls,str) else urls
        cache=self.cache/(hashlib.sha256((key or urls[0]).encode()).hexdigest()+".json")
        saved=load_json(cache,{})
        if ttl and saved.get("at",0)>time.time()-ttl:return saved["body"]
        errors=[]
        for u in urls:
            self.check()
            try:
                headers={}
                if saved.get("etag") and saved.get("url")==u:headers["If-None-Match"]=saved["etag"]
                with self.session().get(u,timeout=(5,18),headers=headers,stream=True) as r:
                    if r.status_code==304:return saved["body"]
                    r.raise_for_status();data=bytearray()
                    for chunk in r.iter_content(65536):
                        self.check();data.extend(chunk)
                        if len(data)>limit:raise ValueError("接口返回的数据过大")
                    value=json.loads(data)
                    atomic_json(cache,{"at":time.time(),"url":u,"etag":r.headers.get("ETag",""),"body":value});return value
            except Cancelled:raise
            except Exception as e:errors.append(str(e))
        raise RuntimeError("请求失败，请检查网络："+str(errors[-1])[:240])
    def manifest(self,force=False):
        key=self.cache/"manifest.json";saved=load_json(key,{})
        if not force and saved.get("at",0)>time.time()-900:return saved["body"]
        endpoints=["https://piston-meta.mojang.com/mc/game/version_manifest_v2.json","https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json"]
        if self.source!="auto":endpoints=self.urls(endpoints[0])
        executor=ThreadPoolExecutor(max_workers=2)
        futures={executor.submit(self.json,[u],u,0):u for u in endpoints}
        try:
            for future in as_completed(futures):
                try:
                    value=future.result()
                    if not isinstance(value.get("versions"),list):continue
                    self.prefer_mirror="bmclapi" in futures[future];atomic_json(key,{"at":time.time(),"body":value});return value
                except Cancelled:raise
                except Exception:continue
        finally:executor.shutdown(wait=False,cancel_futures=True)
        if saved.get("body"):return saved["body"]
        raise RuntimeError("无法获取 Minecraft 版本列表，官方和备用源都未连通")
    def valid(self,path:Path,digest="",algorithm="sha1",size=0):
        if not path.is_file():return False
        stat=path.stat()
        if size and stat.st_size!=size:return False
        if not digest:return stat.st_size>0
        key=(str(path),stat.st_size,stat.st_mtime_ns,algorithm,digest)
        with self._lock:
            if key in self._hashes:return True
        h=hashlib.new(algorithm)
        with path.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):self.check();h.update(chunk)
        ok=h.hexdigest().lower()==digest.lower()
        if ok:
            with self._lock:self._hashes[key]=True
        return ok
    def download(self,url,path:Path,digest="",algorithm="sha1",size=0,progress=None):
        self.check();path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        if self.valid(path,digest,algorithm,size):return path
        part=path.with_name(path.name+".part");last=None
        urls=self.urls(url)
        for attempt in range(3):
            self.check();u=urls[attempt%len(urls)]
            try:
                offset=part.stat().st_size if part.exists() else 0
                headers={"Range":f"bytes={offset}-"} if offset else {}
                with self.session().get(u,stream=True,timeout=(10,30),headers=headers) as r:
                    if r.status_code==416:part.unlink(missing_ok=True);continue
                    r.raise_for_status()
                    resumed=bool(offset and r.status_code==206 and r.headers.get("Content-Range","").startswith(f"bytes {offset}-"))
                    if r.status_code==206 and not resumed:raise ValueError("断点续传响应不匹配")
                    offset=offset if resumed else 0
                    total=size or offset+int(r.headers.get("Content-Length",0));done=offset
                    with part.open("ab" if resumed else "wb") as f:
                        for chunk in r.iter_content(128*1024):
                            self.check();f.write(chunk);done+=len(chunk)
                            if size and done>size:raise ValueError("下载大小超出预期")
                            if progress:progress(done,total)
                    if not self.valid(part,digest,algorithm,size):
                        part.unlink(missing_ok=True);raise ValueError("下载文件校验失败，将自动重试")
                    os.replace(part,path);return path
            except Cancelled:raise
            except Exception as e:last=e;time.sleep(.25*(attempt+1))
        raise RuntimeError(f"下载失败：{path.name}（{last}）")
    def batch(self,jobs,status=None):
        jobs=list({str(j[1]):j for j in jobs}.values());count=0;total=len(jobs)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            futures=[pool.submit(self.download,*job) for job in jobs]
            try:
                for future in as_completed(futures):
                    future.result();count+=1
                    if status:status(count,total)
            except Exception:
                for f in futures:f.cancel()
                raise
