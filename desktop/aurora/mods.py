# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import json,os,re,shutil,uuid,zipfile
from pathlib import Path
from .storage import atomic_json,load_json,safe_path

API="https://api.modrinth.com/v2"
class Modrinth:
    def __init__(self,engine):self.e=engine;self.net=engine.net
    def search(self,query,kind="mod",offset=0):
        import urllib.parse
        facets=[["project_type:"+kind]]
        version=self.e.store.settings.get('selectedVersion','')
        if version and self.e.metadata(version):
            facets.append(["versions:"+self.e.base_version(version)])
            loader=self.e.loader(version)
            if kind=="mod" and loader!="vanilla":facets.append(["categories:"+loader])
        qs=urllib.parse.urlencode({"query":query,"limit":30,"offset":offset,"facets":json.dumps(facets),"index":"relevance"})
        value=self.net.json(API+"/search?"+qs,ttl=120)
        return [{"id":x['project_id'],"title":x['title'],"description":x.get('description',''),"downloads":x.get('downloads',0),"icon":x.get('icon_url') or '',"kind":kind,"author":x.get('author','')} for x in value.get('hits',[])]
    def versions(self,project,kind="mod"):
        import urllib.parse
        version=self.e.store.settings.get('selectedVersion','')
        params={"include_changelog":"false"}
        if version and self.e.metadata(version):
            params['game_versions']=json.dumps([self.e.base_version(version)])
            loader=self.e.loader(version)
            if kind=="mod" and loader!="vanilla":params['loaders']=json.dumps([loader])
        data=self.net.json(API+f"/project/{project}/version?"+urllib.parse.urlencode(params),ttl=180)
        if not data:raise RuntimeError("未找到适用于当前游戏版本和加载器的文件")
        return data
    def install(self,project,kind="mod",version_id=""):
        if kind=="modpack":return self.install_pack(project)
        if not self.e.store.settings.get('selectedVersion'):raise ValueError("请先选择游戏版本")
        if kind=="mod" and self.e.loader(self.e.store.settings['selectedVersion'])=="vanilla":raise ValueError("请先安装并选择 Fabric、Forge 或 Quilt 版本，再安装模组")
        dest=self.e.store.game_dir()/({"mod":"mods","resourcepack":"resourcepacks","shader":"shaderpacks"}.get(kind,"mods"));dest.mkdir(exist_ok=True)
        stage=self.e.store.root/"downloads"/("mods-"+uuid.uuid4().hex);stage.mkdir()
        visited=set();files=[]
        def resolve(pid,exact=None):
            if pid in visited:return
            visited.add(pid)
            value=self.net.json(API+"/version/"+exact,ttl=180) if exact else self.versions(pid,kind)[0]
            file=next((f for f in value['files'] if f.get('primary')),value['files'][0])
            name=file['filename'];target=safe_path(stage,name)
            if Path(name).name!=name:raise ValueError("模组文件名无效")
            hashes=file.get('hashes',{});alg='sha512' if hashes.get('sha512') else 'sha1'
            self.e.emit("下载 "+name)
            self.net.download(file['url'],target,hashes.get(alg,''),alg,file.get('size',0))
            files.append((target,name,pid,value['id']))
            if kind=="mod":
                for dep in value.get('dependencies',[]):
                    if dep.get('dependency_type')=='required' and (dep.get('project_id') or dep.get('version_id')):
                        resolve(dep.get('project_id') or dep['version_id'],dep.get('version_id'))
        try:
            resolve(project,version_id or None)
            manifest=load_json(dest/".aurora-mods.json",{})
            for file,name,pid,vid in files:
                old=manifest.get(pid,{}).get('filename')
                os.replace(file,safe_path(dest,name))
                if old and old!=name:safe_path(dest,old).unlink(missing_ok=True)
                manifest[pid]={"version":vid,"filename":name}
            atomic_json(dest/".aurora-mods.json",manifest)
        finally:shutil.rmtree(stage,ignore_errors=True)
        return "安装完成（含必要依赖）："+str(len(files))+" 个文件"
    def install_pack(self,project):
        value=self.versions(project,"modpack")[0];file=next((f for f in value['files'] if f['filename'].endswith('.mrpack')),None)
        if not file:raise ValueError("此整合包没有 Modrinth 格式文件")
        target=self.e.store.root/"downloads"/(value['id']+".mrpack")
        self.net.download(file['url'],target,file['hashes'].get('sha512',''),'sha512',file.get('size',0))
        return self.import_pack(target)
    def import_pack(self,path):
        path=Path(path)
        with zipfile.ZipFile(path) as z:
            index=json.loads(z.read('modrinth.index.json'))
            if index.get('formatVersion')!=1 or index.get('game')!='minecraft':raise ValueError("不支持此整合包格式")
            deps=index['dependencies'];base=deps['minecraft']
            loader='vanilla';lv=''
            for key,name in [('fabric-loader','fabric'),('quilt-loader','quilt'),('forge','forge'),('neoforge','neoforge')]:
                if key in deps:loader=name;lv=deps[key]
            version=self.e.install(base,loader,lv)
            ident=uuid.uuid4().hex;stage=self.e.store.root/'instances'/(ident+'.stage');game=stage/'game';game.mkdir(parents=True)
            try:
                jobs=[]
                for f in index.get('files',[]):
                    if f.get('env',{}).get('client')=='unsupported':continue
                    target=safe_path(game,f['path']);urls=f.get('downloads',[])
                    if not urls or not urls[0].startswith('https://'):raise ValueError("整合包下载地址无效")
                    hashes=f.get('hashes',{});alg='sha512' if hashes.get('sha512') else 'sha1'
                    jobs.append((urls[0],target,hashes.get(alg,''),alg,f.get('fileSize',0)))
                self.net.batch(jobs,lambda n,t:self.e.emit("安装整合包文件",n,t))
                if sum(i.file_size for i in z.infolist())>3*1024**3:raise ValueError("整合包解压体积过大")
                for name in z.namelist():
                    prefix=next((p for p in ('overrides/','client-overrides/') if name.startswith(p)),None)
                    if prefix and not name.endswith('/'):
                        info=z.getinfo(name)
                        if (info.external_attr>>16)&0o170000==0o120000:raise ValueError("整合包包含不安全链接")
                        p=safe_path(game,name[len(prefix):]);p.parent.mkdir(parents=True,exist_ok=True)
                        with z.open(name) as src,p.open('wb') as out:shutil.copyfileobj(src,out)
                os.replace(stage,self.e.store.root/'instances'/ident)
                obj={"id":ident,"name":index.get('name',path.stem)[:80],"version":version,"notes":"从 Modrinth 整合包导入"}
                self.e.store.instances.append(obj);self.e.store.settings.update(selectedInstance=ident,selectedVersion=version);self.e.store.save()
                return "整合包已安装到独立实例："+obj['name']
            except Exception:shutil.rmtree(stage,ignore_errors=True);raise

