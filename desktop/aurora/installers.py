# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Game-version-specific component choices, with explicit dependency validation.

Workflow reference: Aurora Android's pinned ZalithLauncher2 AddonList and
OptiFine installation design (MovTery and contributors, GPL-3.0-or-later).
This module is a native desktop implementation; no Android classes are bundled.
"""
import hashlib,json,os,re,shutil,subprocess,sys,time,zipfile
from pathlib import Path
from urllib.parse import urlencode,quote
from xml.etree import ElementTree
from .storage import load_json,atomic_json
from .network import Cancelled

COMPONENTS=[('optifine','OptiFine'),('forge','Forge'),('neoforge','NeoForge'),('fabric','Fabric'),('fabric-api','Fabric API'),('quilt','Quilt'),('quilt-api','Quilted Fabric API')]
PRIMARY={'vanilla','fabric','forge','neoforge','quilt','optifine'}

def version_key(value):return tuple((0,int(v)) if v.isdigit() else (1,v) for v in re.findall(r'\d+|[^\d]+',value))

def validate_plan(plan):
    version=plan.get('minecraft','');loader=plan.get('loader','vanilla');chosen=plan.get('loader_version','')
    if not re.fullmatch(r'[A-Za-z0-9_.+\-]+',version):raise ValueError('请选择有效的 Minecraft 版本')
    if loader not in PRIMARY:raise ValueError('加载器类型无效')
    if loader!='vanilla' and not chosen:raise ValueError('请选择加载器的具体版本')
    if chosen and not re.fullmatch(r'[A-Za-z0-9_.+\-]+',chosen):raise ValueError('加载器版本无效')
    if plan.get('fabric-api') and loader!='fabric':raise ValueError('Fabric API 需要 Fabric 加载器')
    if plan.get('quilt-api') and loader!='quilt':raise ValueError('Quilted Fabric API 需要 Quilt 加载器')
    return version,loader,chosen

class InstallerCatalog:
    def __init__(self,engine):self.e=engine;self.net=engine.net
    def _text(self,url):
        path=self.net.cache/(hashlib.sha256(url.encode()).hexdigest()+'.installer.json');saved=load_json(path,{})
        if time.time()-saved.get('at',0)<3600:return saved['body']
        try:
            with self.net.session().get(url,timeout=(8,20),stream=True) as r:
                r.raise_for_status();data=bytearray()
                for chunk in r.iter_content(32768):
                    self.net.check();data.extend(chunk)
                    if len(data)>3*1024*1024:raise ValueError('组件列表过大')
            body=data.decode('utf-8');atomic_json(path,{'at':time.time(),'body':body});return body
        except Exception:
            if saved:return saved['body']
            raise
    def choices(self,kind,version):
        if kind in ('fabric','quilt'):
            api='https://meta.fabricmc.net/v2' if kind=='fabric' else 'https://meta.quiltmc.org/v3'
            data=self.net.json(api+'/versions/loader/'+quote(version),ttl=1800)
            return [{'id':v['loader']['version'],'label':v['loader']['version'],'stable':v['loader'].get('stable',True)} for v in data]
        if kind=='forge':
            urls=['https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml','https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/maven-metadata.xml'];error=None
            for url in urls:
                try:
                    versions=[v.text.split('-',1)[1] for v in ElementTree.fromstring(self._text(url)).findall('./versioning/versions/version') if v.text and v.text.startswith(version+'-')]
                    return [{'id':v,'label':v,'stable':True} for v in sorted(set(versions),key=version_key,reverse=True)]
                except Exception as exc:error=exc
            raise RuntimeError('Forge 版本列表获取失败，可重试') from error
        if kind=='neoforge':
            data=self.net.json('https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge',ttl=1800)
            values=data.get('versions',[]);prefix=None
            match=re.fullmatch(r'1\.(\d+)(?:\.(\d+))?',version)
            if match:prefix=match[1]+'.'+(match[2] or '0')+'.'
            if not prefix and re.fullmatch(r'2\d\.\d+(?:\.\d+)?',version):prefix=version+'.'
            if not prefix:return []
            values=[v for v in values if v.startswith(prefix)]
            return [{'id':v,'label':v,'stable':'beta' not in v} for v in sorted(values,key=version_key,reverse=True)]
        if kind=='optifine':
            data=self.net.json('https://bmclapi2.bangbang93.com/optifine/'+quote(version),ttl=1800)
            values=[{'id':x['type']+'-'+x['patch'],'label':x['type']+' '+x['patch'],'stable':'pre' not in x['patch'].lower(),'meta':x} for x in data if x.get('mcversion') in (version,version+'.0')]
            return sorted(values,key=lambda x:(x['stable'],version_key(x['label'])),reverse=True)
        if kind in ('fabric-api','quilt-api'):
            project='fabric-api' if kind=='fabric-api' else 'qsl';loader='fabric' if kind=='fabric-api' else 'quilt'
            query=urlencode({'game_versions':json.dumps([version]),'loaders':json.dumps([loader])})
            values=self.net.json('https://api.modrinth.com/v2/project/'+project+'/version?'+query,ttl=1800)
            return [{'id':v['id'],'label':v['version_number'],'stable':v.get('version_type')=='release','meta':v} for v in values]
        raise ValueError('未知组件')
    def install(self,plan):
        version,loader,chosen=validate_plan(plan)
        if loader=='optifine':target=self.install_optifine(version,chosen)
        else:target=self.e.install(version,loader,chosen)
        # Install precisely the selected API version into this instance, never an
        # unrelated 'latest' build. Required dependencies follow Modrinth metadata.
        from .mods import Modrinth
        previous=self.e.store.settings.get('selectedVersion','');self.e.store.settings['selectedVersion']=target
        try:
            for kind in ('fabric-api','quilt-api'):
                if plan.get(kind):
                    value=self.net.json('https://api.modrinth.com/v2/version/'+quote(plan[kind]),ttl=1800)
                    if version not in value.get('game_versions',[]) or loader not in value.get('loaders',[]):raise ValueError('所选 API 不兼容当前游戏和加载器')
                    Modrinth(self.e).install(value['project_id'],'mod',plan[kind])
        finally:self.e.store.settings['selectedVersion']=previous
        return target
    def install_optifine(self,version,chosen):
        choice=next((v for v in self.choices('optifine',version) if v['id']==chosen),None)
        if not choice:raise ValueError('所选 OptiFine 已不可用，请刷新列表')
        meta=choice['meta'];self.e.install(version);java=self.e.java_for(version)
        url='https://bmclapi2.bangbang93.com/optifine/'+quote(meta['mcversion'])+'/'+quote(meta['type'])+'/'+quote(meta['patch'])
        jar=self.net.download(url,self.e.store.root/'downloads'/('OptiFine-'+version+'-'+chosen+'.jar'))
        with zipfile.ZipFile(jar) as z:
            if 'optifine/Installer.class' not in z.namelist():raise ValueError('下载文件不是有效的 OptiFine 安装器')
        profiles=self.e.root/'launcher_profiles.json'
        if not profiles.exists():atomic_json(profiles,{'profiles':{}})
        from .branding import agent_path
        before=set(self.e.local_versions()[i]['id'] for i in range(len(self.e.local_versions())))
        command=[java,'-Djava.awt.headless=true','-cp',str(agent_path())+os.pathsep+str(jar),'io.github.reunionsama.aurora.OptiFineBridge',str(self.e.root)]
        self.e.emit('正在安装 OptiFine');flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=flags)
        deadline=time.monotonic()+180
        import threading
        threading.Thread(target=lambda:[self.e.log(line.rstrip()) for line in process.stdout],daemon=True).start()
        while process.poll() is None:
            if self.net.cancel.wait(.15) or time.monotonic()>deadline:process.kill();process.wait();raise Cancelled('OptiFine 安装已取消或超时')
        if process.returncode:raise RuntimeError('OptiFine 安装失败，请查看实时日志')
        choices=[x['id'] for x in self.e.local_versions() if 'optifine' in x['id'].lower() and self.e.base_version(x['id'])==version]
        if not choices:raise RuntimeError('OptiFine 安装器未生成游戏配置')
        target=next((v for v in choices if v not in before),choices[0]);profile=self.e.metadata(target);profile['jar']=version;atomic_json(self.e.root/'versions'/target/(target+'.json'),profile);self.e._files(profile)
        return target
