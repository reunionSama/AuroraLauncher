# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Modrinth retry/cache policy. Download integrity remains enforced by Net."""
import hashlib,json,threading,time
from urllib.parse import urlsplit
import requests
from .storage import atomic_json,load_json
from .network import Cancelled

OFFICIAL='https://api.modrinth.com/v2'

def validate_endpoint(value):
    value=value.strip().rstrip('/')
    url=urlsplit(value)
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('备用接口必须是完整的 HTTPS 地址，且不能包含账号、密码或查询参数。')
    if not url.path.endswith('/v2'):raise ValueError('备用接口地址须以 /v2 结尾。')
    return value

class ModrinthAPI:
    def __init__(self,engine):
        self.net=engine.net;self.notice='';self.alternate=engine.store.settings.get('modrinthApi','')
        if self.alternate:validate_endpoint(self.alternate)
        if not hasattr(self.net,'_modrinth_gate'):
            self.net._modrinth_gate=threading.Lock();self.net._modrinth_next={}
    def json(self,url,ttl=180,stale=False):
        if not url.startswith(OFFICIAL+'/'):raise ValueError('资源接口地址无效')
        key=self.net.cache/('modrinth-'+hashlib.sha256(url.encode()).hexdigest()+'.json')
        saved=load_json(key,{})
        if time.time()-saved.get('at',0)<ttl and 'body' in saved:return saved['body']
        endpoints=([self.alternate+url[len(OFFICIAL):]] if self.alternate and self.alternate!=OFFICIAL else [])+[url]
        errors=[]
        for endpoint in endpoints:
            host=urlsplit(endpoint).netloc
            for attempt in range(3):
                self.net.check()
                with self.net._modrinth_gate:wait=self.net._modrinth_next.get(host,0)-time.monotonic()
                if wait>3:break # honour cooldown, don't freeze a UI task for minutes
                if wait>0 and self.net.cancel.wait(wait):self.net.check()
                try:
                    headers={'If-None-Match':saved['etag']} if saved.get('etag') and saved.get('url')==endpoint else {}
                    with self.net.session().get(endpoint,timeout=(4,12),stream=True,headers=headers) as response:
                        if response.status_code==304 and 'body' in saved:
                            saved['at']=time.time();atomic_json(key,saved);return saved['body']
                        if response.status_code==429:
                            try:delay=max(1,min(300,float(response.headers.get('Retry-After') or response.headers.get('X-Ratelimit-Reset') or 5)))
                            except ValueError:delay=5
                            with self.net._modrinth_gate:self.net._modrinth_next[host]=time.monotonic()+delay
                            errors.append('接口限流');continue
                        response.raise_for_status();data=bytearray()
                        for chunk in response.iter_content(65536):
                            self.net.check();data.extend(chunk)
                            if len(data)>8*1024*1024:raise ValueError('资源列表过大')
                        body=json.loads(data)
                        atomic_json(key,{'at':time.time(),'url':endpoint,'etag':response.headers.get('ETag',''),'body':body})
                        self.notice='已连接备用资源接口' if endpoint!=url else ''
                        return body
                except Cancelled:raise
                except (requests.RequestException,ValueError) as exc:
                    errors.append(type(exc).__name__)
                    code=getattr(getattr(exc,'response',None),'status_code',0)
                    if code and code<500 and code!=429:break
                    if attempt<2 and self.net.cancel.wait(.35*(2**attempt)):self.net.check()
        if stale and 'body' in saved and time.time()-saved.get('at',0)<86400:
            self.notice='网络暂时不可用，显示上次缓存；安装时仍需联网校验。';return saved['body']
        raise RuntimeError('Modrinth 暂时无法连接或被限流，请稍后重试；可在设置中配置 HTTPS 备用接口。')
