# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import json,os,re,shlex,shutil,subprocess,sys,threading,time,uuid,zipfile
from pathlib import Path
from minecraft_launcher_lib import command,forge,runtime,mod_loader
from minecraft_launcher_lib._helper import parse_rule_list
from minecraft_launcher_lib.natives import get_natives
from . import VERSION,CLIENT_ID
from .storage import atomic_json,load_json,safe_path,redact
from .network import Net,Cancelled

class Engine:
    def __init__(self,store,progress=lambda *x:None,log=lambda x:None,cancel=None):
        self.store=store;self.root=store.library;self.root.mkdir(parents=True,exist_ok=True)
        self.cancel=cancel or threading.Event();self.progress=progress;self.log=log
        self.net=Net(store.root/"cache",store.settings["source"],store.settings["workers"],self.cancel)
        self.process=None;self.process_lock=threading.Lock();self._last_emit=0
    def emit(self,text,n=0,total=0):
        self.net.check();now=time.monotonic()
        if now-self._last_emit>=.07 or (total and n==total):self._last_emit=now;self.progress(text,n,total)
    def local_versions(self):
        values=[]
        for f in (self.root/"versions").glob("*/*.json"):
            data=load_json(f,{})
            if data.get("id")!=f.stem:continue
            values.append({"id":f.stem,"type":data.get("type","custom"),"base":self.base_version(f.stem),"loader":self.loader(f.stem)})
        return sorted(values,key=lambda x:x["id"],reverse=True)
    def metadata(self,version):
        if not re.fullmatch(r"[A-Za-z0-9_.+\-]+",version):raise ValueError("版本标识无效")
        return load_json(self.root/"versions"/version/(version+".json"),{})
    def base_version(self,version):
        data=self.metadata(version);seen=set()
        while data.get("inheritsFrom") and data["inheritsFrom"] not in seen:
            version=data["inheritsFrom"];seen.add(version);data=self.metadata(version)
        return version
    def loader(self,version):
        data=self.metadata(version);text=(version+json.dumps(data.get("libraries",[]))).lower()
        for key in ("neoforge","quilt","fabric","forge","optifine"):
            if key in text:return key
        return "vanilla"
    def _job(self,meta,path):return (meta["url"],path,meta.get("sha1",""),"sha1",meta.get("size",0))
    def install(self,version,loader="vanilla",loader_version="",repair=False):
        self.emit("正在读取版本信息")
        path=self.root/"versions"/version/(version+".json")
        data=self.metadata(version)
        if not data or repair:
            manifest=self.net.manifest();item=next((v for v in manifest["versions"] if v["id"]==version),None)
            if item:
                self.net.download(item["url"],path,item.get("sha1",""));data=json.loads(path.read_text("utf-8"))
            elif not data:raise ValueError("未找到此游戏版本")
        if data.get("inheritsFrom"):
            self.install(data["inheritsFrom"],repair=repair)
        self._files(data)
        java=self.java_for(version)
        if loader in ("fabric","quilt"):
            api="https://meta.fabricmc.net/v2" if loader=="fabric" else "https://meta.quiltmc.org/v3"
            if not loader_version:
                choices=self.net.json(f"{api}/versions/loader/{version}",ttl=3600)
                if not choices:raise ValueError("此 Minecraft 版本尚无对应加载器")
                loader_version=choices[0]["loader"]["version"]
            self.emit("正在安装 "+loader.capitalize()+" "+loader_version)
            profile=self.net.json(f"{api}/versions/loader/{version}/{loader_version}/profile/json",ttl=3600)
            if not isinstance(profile,dict) or not re.fullmatch(r"[A-Za-z0-9_.+\-]+",profile.get("id","")):raise ValueError("加载器返回了无效版本信息")
            profile['jar']=version
            target=profile["id"];atomic_json(self.root/"versions"/target/(target+".json"),profile)
            self._files(profile);return target
        if loader in ("forge","neoforge"):
            self.emit("正在安装 "+loader+"；首次安装需要处理游戏库")
            provider=mod_loader.get_mod_loader(loader)
            chosen=loader_version or None
            if loader=="forge" and chosen and chosen.startswith(version+"-"):
                chosen=chosen[len(version)+1:]
            target=self._install_neoforge(version,chosen,java) if loader=='neoforge' else provider.install(version,str(self.root),loader_version=chosen,callback=self.callbacks(),java=java)
            profile=self.metadata(target)
            if not profile:raise RuntimeError("加载器安装器结束，但未找到完整版本")
            if profile.get('inheritsFrom') and not profile.get('jar'):
                profile['jar']=version;atomic_json(self.root/'versions'/target/(target+'.json'),profile)
            return target
        self.emit("安装完成",1,1);return version
    def _install_neoforge(self,version,chosen,java):
        # The library's legacy version normalizer prepends '1.' and rejects the
        # new year-based Minecraft versions. The official installer knows them.
        from .installers import InstallerCatalog
        if not chosen:
            choices=InstallerCatalog(self).choices('neoforge',version)
            if not choices:raise ValueError('此 Minecraft 版本尚无对应加载器')
            chosen=choices[0]['id']
        if not re.fullmatch(r'[A-Za-z0-9_.+\-]+',chosen):raise ValueError('NeoForge 版本无效')
        jar=self.net.download(f'https://maven.neoforged.net/releases/net/neoforged/neoforge/{chosen}/neoforge-{chosen}-installer.jar',self.store.root/'downloads'/('neoforge-'+chosen+'-installer.jar'))
        with zipfile.ZipFile(jar) as z:
            profile=json.loads(z.read('install_profile.json'));client=json.loads(z.read('version.json'))
        if profile.get('minecraft',client.get('inheritsFrom'))!=version:raise ValueError('NeoForge 安装器不兼容所选游戏版本')
        if not (self.root/'launcher_profiles.json').exists():atomic_json(self.root/'launcher_profiles.json',{'profiles':{}})
        flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
        process=subprocess.Popen([java,'-jar',str(jar),'--install-client',str(self.root)],cwd=self.store.root/'downloads',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=flags)
        threading.Thread(target=lambda:[self.log(line.rstrip()) for line in process.stdout],daemon=True).start()
        deadline=time.monotonic()+600
        while process.poll() is None:
            if self.cancel.wait(.15) or time.monotonic()>deadline:process.kill();process.wait();raise Cancelled('NeoForge 安装已取消或超时')
        if process.returncode:raise RuntimeError('NeoForge 安装失败，请查看实时日志')
        target=client.get('id','neoforge-'+chosen)
        if not self.metadata(target):raise RuntimeError('NeoForge 安装器未生成游戏配置')
        return target
    def callbacks(self):
        state={"max":0,"text":"准备游戏组件"}
        def status(x):state['text']=str(x);self.emit(state['text'])
        def maximum(x):state['max']=max(1,int(x))
        def progress(x):self.emit(state['text'],int(x),state['max'])
        return {"setStatus":status,"setMax":maximum,"setProgress":progress}
    def _files(self,data):
        version=data["id"];jobs=[];natives=[]
        self.emit("正在校验游戏库")
        for lib in data.get("libraries",[]):
            if lib.get("rules") and not parse_rule_list(lib["rules"],{}):continue
            downloads=lib.get("downloads",{})
            artifact=downloads.get("artifact")
            if artifact and artifact.get("url"):
                jobs.append(self._job(artifact,safe_path(self.root/"libraries",artifact["path"])))
            elif not downloads:
                parts=lib["name"].split(":")
                if len(parts)<3:continue
                group,name,ver=parts[:3];ext="jar"
                if "@" in ver:ver,ext=ver.split("@",1)
                classifier=("-"+parts[3]) if len(parts)>3 else ""
                rel=group.replace(".","/")+f"/{name}/{ver}/{name}-{ver}{classifier}.{ext}"
                jobs.append((lib.get("url","https://libraries.minecraft.net/").rstrip("/")+"/"+rel,safe_path(self.root/"libraries",rel)))
            native=get_natives(lib)
            if native:
                meta=downloads.get("classifiers",{}).get(native)
                if meta:
                    dest=safe_path(self.root/"libraries",meta.get("path",lib['name'].replace(":","/")+"-"+native+".jar"))
                    jobs.append(self._job(meta,dest));natives.append((dest,lib.get("extract",{}).get("exclude",[])))
        if data.get("downloads",{}).get("client"):
            jobs.append(self._job(data["downloads"]["client"],self.root/"versions"/version/(version+".jar")))
        logging=data.get("logging",{}).get("client",{}).get("file")
        if logging:jobs.append(self._job(logging,safe_path(self.root/"assets/log_configs",logging["id"])))
        mappings=data.get('downloads',{}).get('client_mappings')
        if mappings and self.store.settings.get('gameBranding',True):jobs.append(self._job(mappings,self.root/'assets/mappings'/(version+'.txt')))
        self.net.batch(jobs,lambda n,t:self.emit("下载游戏与运行库",n,t))
        for archive,exclude in natives:
            self.extract_zip(archive,self.root/"versions"/version/"natives",exclude)
        index=data.get("assetIndex")
        if index:
            target=safe_path(self.root/"assets/indexes",index["id"]+".json")
            self.net.download(*self._job(index,target))
            assets=json.loads(target.read_text("utf-8"));jobs=[]
            for obj in assets.get("objects",{}).values():
                h=obj["hash"]
                if not re.fullmatch("[a-f0-9]{40}",h):raise ValueError("资源哈希格式无效")
                jobs.append((f"https://resources.download.minecraft.net/{h[:2]}/{h}",self.root/"assets/objects"/h[:2]/h,h,"sha1",obj.get("size",0)))
            self.net.batch(jobs,lambda n,t:self.emit("并行下载游戏资源",n,t))
            if assets.get("virtual") or assets.get("map_to_resources"):
                root=self.root/"assets/virtual"/index["id"] if assets.get("virtual") else self.root/"resources"
                for name,obj in assets["objects"].items():
                    self.net.check();dest=safe_path(root,name);dest.parent.mkdir(parents=True,exist_ok=True)
                    src=self.root/"assets/objects"/obj["hash"][:2]/obj["hash"]
                    if not dest.exists():
                        try:os.link(src,dest)
                        except OSError:shutil.copyfile(src,dest)
        atomic_json(self.root/"versions"/version/"aurora-verified.json",{"at":time.time(),"version":version})
    @staticmethod
    def extract_zip(archive,root,exclude=()):
        root=Path(root);root.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            if sum(i.file_size for i in z.infolist())>3*1024**3:raise ValueError("压缩包解压体积过大")
            for i in z.infolist():
                name=i.filename
                if any(name.startswith(e) for e in exclude) or name.endswith("/"):continue
                if (i.external_attr>>16)&0o170000==0o120000:raise ValueError("压缩包包含不安全链接")
                p=safe_path(root,name);p.parent.mkdir(parents=True,exist_ok=True)
                with z.open(i) as src,p.open("wb") as out:shutil.copyfileobj(src,out)
    def java_for(self,version):
        data=self.metadata(version)
        if data.get("inheritsFrom"):data=self.metadata(self.base_version(version))
        info=data.get("javaVersion",{})
        major=info.get("majorVersion",8)
        configured=self.store.settings.get("java","")
        choices=[configured,shutil.which("java")]
        component=info.get("component") or ("java-runtime-gamma" if major>=17 else "jre-legacy")
        choices.insert(1,runtime.get_executable_path(component,str(self.root)))
        for path in choices:
            if path and Path(path).is_file():
                try:
                    flags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
                    output=subprocess.run([str(path),"-version"],capture_output=True,text=True,timeout=8,creationflags=flags)
                    text=output.stderr+output.stdout;match=re.search(r'version\s+"(?:1\.)?(\d+)',text)
                    if match and int(match[1])==major:return str(path)
                except (OSError,subprocess.SubprocessError):pass
        self.emit(f"自动安装官方 Java {major} 运行环境")
        runtime.install_jvm_runtime(component,str(self.root),callback=self.callbacks(),max_workers=self.store.settings["workers"])
        executable=runtime.get_executable_path(component,str(self.root))
        if not executable:raise RuntimeError("Java 安装不完整，请在设置中选择对应 Java")
        return executable
    def make_command(self,version,account,game_dir,server="",demo=False):
        from .branding import branding_args
        java=self.java_for(version);s=self.store.settings
        args=shlex.split(s.get("jvmArgs", ""),posix=sys.platform!="win32")
        if any(x.startswith(("-cp","-classpath","--class-path","-jar")) for x in args):raise ValueError("自定义 JVM 参数不能替换游戏主类或 classpath")
        options={"username":account["name"],"uuid":account["uuid"],"token":account.get("access_token","0"),"executablePath":java,
                 "launcherName":"AuroraLauncher","clientId":CLIENT_ID,"launcherVersion":VERSION,"gameDirectory":str(game_dir),"jvmArguments":[f"-Xmx{int(s['memory'])}M","-Xms512M",*branding_args(self,version),*args],
                 "customResolution":True,"resolutionWidth":str(s['width']),"resolutionHeight":str(s['height']),"enableLoggingConfig":True,"demo":demo}
        if server:
            if not re.fullmatch(r"[A-Za-z0-9_.:\-\[\]]{1,255}",server):raise ValueError("服务器地址格式无效")
            base=self.metadata(self.base_version(version))
            if 'is_quick_play_multiplayer' in json.dumps(base.get('arguments',{})):
                options['quickPlayPath']=str(self.store.root/'cache'/'quickplay.json')
                options['quickPlayMultiplayer']=server
            else:
                host,sep,port=server.rpartition(":")
                options["server"]=host if sep and port.isdigit() else server
                if sep and port.isdigit():options["port"]=port
        args=command.get_minecraft_command(version,str(self.root),options)
        return [x.replace('${clientid}',CLIENT_ID).replace('${client_id}',CLIENT_ID).replace('${auth_xuid}',account.get('xuid','')) for x in args]
    def launch(self,version,account,game_dir,on_exit=lambda c:None,server="",demo=False):
        with self.process_lock:
            if self.process and self.process.poll() is None:raise RuntimeError("当前实例已经在运行")
            self.emit("正在校验游戏文件")
            self.install(version)
            args=self.make_command(version,account,game_dir,server,demo)
            game_dir=Path(game_dir);game_dir.mkdir(parents=True,exist_ok=True)
            self.log("启动 Minecraft "+version+" · "+self.loader(version))
            flags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0
            p=subprocess.Popen(args,cwd=game_dir,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=flags,text=True,encoding="utf-8",errors="replace",bufsize=1)
            self.process=p
        self.emit("游戏已启动",1,1)
        def read():
            try:
                for line in p.stdout:self.log(redact(line.rstrip()))
            finally:
                code=p.wait();self.log(f"Minecraft 进程退出，退出码 {code}");on_exit(code)
        threading.Thread(target=read,daemon=True,name="Aurora-game-log").start();return p.pid
    def stop(self):
        with self.process_lock:
            if self.process and self.process.poll() is None:self.process.terminate()

