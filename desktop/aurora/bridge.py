# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import json,os,re,shutil,socket,subprocess,sys,threading,time,traceback,uuid,zipfile
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor,as_completed
from PySide6.QtCore import QObject,Property,Signal,Slot,QTimer,QUrl
from PySide6.QtGui import QDesktopServices,QGuiApplication
from PySide6.QtWidgets import QFileDialog
from . import VERSION,BUILD,CLIENT_ID,PROJECT,MOBILE_PROJECT,SPONSOR
from .storage import Store,Vault,atomic_json,load_json,safe_path,redact
from .network import Net,Cancelled
from .engine import Engine
from .auth import Auth,offline,verification_url
from .skins import SkinCache
from .updates import UpdateChecker
from .installers import InstallerCatalog,COMPONENTS,validate_plan
from .i18n import translate,LANGUAGES
from .mods import Modrinth
from .terracotta import Terracotta

class Bridge(QObject):
    installerChanged=Signal()
    dataChanged=Signal();settingsChanged=Signal();runtimeChanged=Signal();logsChanged=Signal();tasksChanged=Signal()
    message=Signal(str,str);deviceReady=Signal(str,str);updateReady=Signal(str,str)
    _done=Signal(str,object,str);_progress=Signal(str,int,int);_line=Signal(str);_exited=Signal(int);_device=Signal(str,str)
    def __init__(self,store:Store,assets:Path,test_mode=False):
        super().__init__();self.store=store;self.assets=assets;self.test_mode=test_mode;self.pool=ThreadPoolExecutor(max_workers=5,thread_name_prefix='Aurora');self.catalog_pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix='Aurora-catalog')
        self.cancel=threading.Event();self.engine=Engine(store,self._progress.emit,self._line.emit,self.cancel);self.terra=Terracotta(self.engine)
        self._catalog_generation=0;self._installer={'minecraft':'','rows':[]}
        self.updater=UpdateChecker(store.root/'cache')
        self._skin_cancel=threading.Event();self.skins=SkinCache(store.root/'cache',self._skin_cancel);self._skin_identity=None;self._skin_generation=0;self._skin_model='classic';self._skin_status='默认皮肤';self._cape=''
        self.vault=Vault(store.root);self.accounts=[];self._vault_error=''
        try:self.accounts=self.vault.read()
        except Exception:self._vault_error='账号数据无法解密，请重新登录微软账号。'
        self._all=[];self._versions=[];self._local=[];self._results=[];self._files=[];self._diagnostics=[];self._java=[];self._worlds=[];self._updates=None;self._skin=str(assets/'aurora_skin.png');self._jobs={};self._tasks=[];self._log=deque(maxlen=1800);self._logdirty=False;self._filekind='mods';self._query='';self._snapshots=False;self._search_id=0;self._pending={};self._terra_index=-1;self._terra_session='';self._terra_failures=0
        self._runtime={'busy':False,'status':'准备就绪','progress':0.0,'running':False,'pid':0,'authCode':'','authUrl':'','room':'','roomState':'未连接','roomAddress':'','roomMembers':[],'catalogLoading':False,'error':'','updateTitle':'','updateBody':''}
        self._done.connect(self._finish);self._progress.connect(self._on_progress);self._line.connect(self._append_log);self._exited.connect(self._game_exit);self._device.connect(self._on_device)
        self.logtimer=QTimer(self);self.logtimer.timeout.connect(self._flush_logs);self.logtimer.start(150)
        self.terratimer=QTimer(self);self.terratimer.timeout.connect(self._poll_terra);self.terratimer.start(1500)
        self._save_timer=QTimer(self);self._save_timer.setSingleShot(True);self._save_timer.timeout.connect(self.store.save)
        self._logfile=(store.root/'logs'/'launcher-latest.log').open('a',encoding='utf-8',buffering=1)
        self._append_log('AuroraLauncher Desktop '+VERSION+' · 全新桌面移植')
        self.refresh()
        if not test_mode:
            QTimer.singleShot(350,self.fetchVersions)
            if self.store.settings['autoUpdate']:QTimer.singleShot(1600,lambda:self.checkUpdate(False))
    @Property('QVariantMap',notify=settingsChanged)
    def settings(self):return dict(self.store.settings)
    @Property('QVariantMap',notify=installerChanged)
    def installer(self):return self._installer
    @Property('QVariantMap',notify=runtimeChanged)
    def runtime(self):return dict(self._runtime)
    @Property('QVariantList',notify=dataChanged)
    def versions(self):return self._versions
    @Property('QVariantList',notify=dataChanged)
    def localVersions(self):return self._local
    @Property('QVariantList',notify=dataChanged)
    def accountList(self):return [{k:v for k,v in a.items() if k in ('id','name','kind','uuid')} for a in self.accounts]
    @Property('QVariantList',notify=dataChanged)
    def instances(self):return self.store.instances
    @Property('QVariantList',notify=dataChanged)
    def modResults(self):return self._results
    @Property('QVariantList',notify=dataChanged)
    def localFiles(self):return self._files
    @Property('QVariantList',notify=dataChanged)
    def diagnostics(self):return self._diagnostics
    @Property('QVariantList',notify=dataChanged)
    def javaList(self):return self._java
    @Property('QVariantList',notify=dataChanged)
    def worlds(self):return self._worlds
    @Property('QVariantList',notify=tasksChanged)
    def tasks(self):return self._tasks
    @Property(str,notify=logsChanged)
    def logText(self):return '\n'.join(self._log)
    @Property(str,notify=dataChanged)
    def skinPath(self):return self._skin
    @Property(str,notify=dataChanged)
    def capePath(self):return self._cape
    @Property(str,notify=dataChanged)
    def skinModel(self):return self._skin_model
    @Property(str,notify=dataChanged)
    def skinStatus(self):return self._skin_status
    @Property(str,constant=True)
    def version(self):return VERSION
    @Slot(str,result=str)
    def translate(self,text):return translate(text,self.store.settings.get('language','zh_CN'))
    @Property(str,constant=True)
    def clientId(self):return CLIENT_ID
    @Property(str,notify=dataChanged)
    def currentAccountName(self):return self.account().get('name','尚未添加账号')
    @Property(str,notify=dataChanged)
    def currentInstanceName(self):return self.store.instance()['name']
    def account(self):return next((a for a in self.accounts if a['id']==self.store.settings.get('selectedAccount')),self.accounts[0] if self.accounts else {})
    def _set(self,**values):self._runtime.update(values);self.runtimeChanged.emit()
    def submit(self,key,fn,busy=False):
        if key in self._jobs:return
        if busy and self._runtime['busy']:self.message.emit('任务正在进行','请等待当前任务完成，或先取消它。');return
        if busy:
            self.cancel.clear();self._set(busy=True,status='正在准备',progress=0,error='')
            task={'id':key,'title':key,'status':'进行中','progress':0};self._tasks.insert(0,task);self._tasks=self._tasks[:30];self.tasksChanged.emit()
        self._jobs[key]=busy
        def run():
            try:self._done.emit(key,fn(),'')
            except Exception as e:
                error=redact(str(e));self._line.emit(type(e).__name__+': '+error);self._done.emit(key,None,error)
        (self.catalog_pool if key.startswith('component-') else self.pool).submit(run)
    @Slot(str,object,str)
    def _finish(self,key,value,error):
        busy=self._jobs.pop(key,False)
        if busy:
            self._set(busy=False,status='已取消' if self.cancel.is_set() else ('任务失败' if error else '已完成'),progress=0 if error else 1)
            for task in self._tasks:
                if task['id']==key:task['status']='失败 / 已取消' if error else '已完成';task['progress']=0 if error else 1;break
            self.tasksChanged.emit();self.cancel.clear()
        if error:
            if key.startswith('component-'):self._catalog_result(key,[],error)
            elif key=='versions':self._set(catalogLoading=False);self.message.emit('版本列表暂时不可用',error)
            elif key=='terra-poll':
                self._terra_failures+=1
                if self._terra_failures>=5:self.terra.port=0;self._set(roomState='陶瓦连接已断开，请重新启动')
            elif key.startswith('skin-'):
                if key==f'skin-{self._skin_generation}':self._skin_status='皮肤加载失败，可在账号页重试';self.dataChanged.emit()
            elif key=='update-auto':self._append_log('自动检查更新：'+error)
            else:self.message.emit('操作未完成',error)
            return
        if key.startswith('component-'):self._catalog_result(key,value,'')
        elif key=='versions':self._all=value;self._set(catalogLoading=False);self.filterVersions(self._query,self._snapshots)
        elif key.startswith('search-'):
            if key==f'search-{self._search_id}':self._results=value;self.dataChanged.emit()
        elif key in ('login','refresh-account'):
            self.accounts=[a for a in self.accounts if a['id']!=value['id']]+[value];self.vault.write(self.accounts);self.store.settings['selectedAccount']=value['id'];self.store.save();self._set(authCode='',authUrl='');self.refresh();self.message.emit('登录成功',value['name']+' 已添加')
        elif key.startswith('install-'):
            self.store.settings['selectedVersion']=value;self.store.instance()['version']=value;self.store.save();self.refresh();self.message.emit('安装完成',value+' 已可以启动')
        elif key=='launch':self._set(running=True,pid=int(value),status='游戏已启动');self.dataChanged.emit()
        elif key=='diagnostics':self._diagnostics=value;self.dataChanged.emit()
        elif key=='scan-java':self._java=value;self.dataChanged.emit();self.message.emit('Java 检测完成','发现 '+str(len(value))+' 个 Java 环境')
        elif key.startswith('skin-'):
            if key==f'skin-{self._skin_generation}' and self.store.settings.get('skinMode','account')=='account':
                account=self.account();account.update(value['meta']);self.vault.write(self.accounts)
                self._skin_identity=self._skin_key();self._cape=value.get('cape_path','')
                if value['path']:self._skin=value['path'];self._skin_model=value['meta'].get('skin_model','classic')
                self._skin_status=value['warning'] or ('玩家皮肤 · '+account.get('name',''))
                self.dataChanged.emit()
        elif key in ('terra-host','terra-join','terra-leave','terra-poll'):self._show_terra(value)
        elif key.startswith('update-'):
            self._updates=value['candidate']
            self._append_log('检查更新：'+value['message'])
            if self._updates:
                v=self._updates;self._set(updateTitle=v['title'],updateBody=v['body']);self.updateReady.emit(v['title'],v['body'])
            elif key=='update-manual':self.message.emit('检查更新',value['message'])
        elif key=='download-update':self.message.emit('新版已下载',str(value)+'\n请打开下载目录运行新版 EXE。');QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(value).parent)))
        elif key in ('install-mod','import-pack'):
            self.refresh();self.message.emit('资源安装完成',str(value))
        elif key in ('backup','restore','export-instance'):self.refresh();self.message.emit('操作完成',str(value))
        elif isinstance(value,str):self.message.emit('完成',value)
        self.settingsChanged.emit()
    @Slot(str,int,int)
    def _on_progress(self,text,n,total):
        self._set(status=text,progress=max(0,min(1,n/total)) if total else -1)
        now=time.monotonic()
        if now-getattr(self,'_last_task_update',0)>.25:
            self._last_task_update=now
            for task in self._tasks:
                if task['status']=='进行中':task.update(title=text,progress=self._runtime['progress']);break
            self.tasksChanged.emit()
    @Slot(str)
    def _append_log(self,text):
        text=redact(str(text));self._log.append(time.strftime('%H:%M:%S')+'  '+text);self._logdirty=True
        if hasattr(self,'_logfile'):self._logfile.write(text+'\n')
    def _flush_logs(self):
        if self._logdirty:self._logdirty=False;self.logsChanged.emit()
    @Slot(int)
    def _game_exit(self,code):
        self._set(running=False,pid=0,status='游戏已退出' if code==0 else '游戏异常退出')
        if code:
            text='\n'.join(self._log)[-30000:]
            hint='请在实时日志中查看最后的错误。'
            if 'OutOfMemoryError' in text:hint='可能内存不足，请调整游戏内存并减少高负载模组。'
            elif 'UnsupportedClassVersion' in text:hint='Java 版本不匹配，请使用游戏要求的 Java 版本。'
            elif 'GLFW' in text or 'OpenGL' in text:hint='请更新显卡驱动；虚拟机通常不具备运行游戏所需的 OpenGL。'
            self.message.emit('Minecraft 退出码 '+str(code),hint)
    @Slot(str,str)
    def _on_device(self,code,url):self._set(authCode=code,authUrl=url);self.deviceReady.emit(code,url)
    @Slot()
    def cancelTask(self):self.cancel.set();self._set(status='正在取消，等待当前文件结束')
    @Slot(str,'QVariant')
    def setSetting(self,key,value):
        if key not in self.store.settings:return
        if key=='language' and value not in LANGUAGES:return
        if self._runtime['busy'] and key in ('java','library','source','workers','selectedVersion','selectedInstance'):return
        if key in ('memory','width','height','workers','interval','fps'):
            bounds={'memory':(512,65536),'width':(640,7680),'height':(480,4320),'workers':(2,32),'interval':(5,60),'fps':(30,60)};lo,hi=bounds[key];value=max(lo,min(hi,int(value)))
        elif key in ('brightness','speed','hue'):value=max(0,min(1,float(value)))
        elif isinstance(self.store.settings[key],bool):value=bool(value)
        self.store.settings[key]=value
        if key=='workers':self.engine.net.workers=int(value)
        if key=='source':self.engine.net.source=value;self.engine.net.prefer_mirror=value=='bmclapi'
        if key=='selectedVersion':self.store.instance()['version']=value
        self._save_timer.start(300);self.settingsChanged.emit()
        if key in ('selectedInstance','library','selectedVersion'):self.refresh()
    @Slot(int,int)
    def rememberWindow(self,width,height):
        if not self.test_mode:self.store.settings.update(windowWidth=max(960,min(7680,width)),windowHeight=max(620,min(4320,height)));self.store.save()
    @Slot(str)
    def selectAccount(self,ident):self.store.settings['selectedAccount']=ident;self.store.save();self.refresh()
    @Slot(str)
    def addOffline(self,name):
        try:
            value=offline(name);self.accounts=[a for a in self.accounts if a['id']!=value['id']]+[value];self.vault.write(self.accounts);self.store.settings['selectedAccount']=value['id'];self.store.save();self.refresh()
        except Exception as e:self.message.emit('无法添加',str(e))
    @Slot(str)
    def removeAccount(self,ident):
        self.accounts=[a for a in self.accounts if a['id']!=ident];self.vault.write(self.accounts)
        if self.store.settings['selectedAccount']==ident:self.store.settings['selectedAccount']=self.accounts[0]['id'] if self.accounts else ''
        self.store.save();self.refresh()
    @Slot()
    def microsoftLogin(self):
        def job():
            auth=Auth(self.cancel);device=auth.start();self._device.emit(device['user_code'],verification_url(device));return auth.poll(device)
        self.submit('login',job,True)
    @Slot()
    def openLoginPage(self):QDesktopServices.openUrl(QUrl(verification_url({'verification_uri':self._runtime.get('authUrl') or 'https://microsoft.com/link'})))
    @Slot(str)
    def copyText(self,text):QGuiApplication.clipboard().setText(text)
    @Slot()
    def fetchVersions(self):
        self._set(catalogLoading=True);self.submit('versions',lambda:self.engine.net.manifest(True)['versions'])
    @Slot(str,bool)
    def filterVersions(self,query,snapshots=False):
        self._query=query;self._snapshots=snapshots;installed={v['id'] for v in self._local}
        self._versions=[{'id':x['id'],'type':x['type'],'date':x.get('releaseTime','')[:10],'installed':x['id'] in installed} for x in self._all if query.lower() in x['id'].lower() and (snapshots or x['type']=='release')][:250];self.dataChanged.emit()
    @Slot(str,str)
    def installVersion(self,version,loader='vanilla'):self.submit('install-'+version,lambda:self.engine.install(version,loader),True)
    @Slot(str)
    def prepareInstaller(self,version):
        if not version:version=self.engine.base_version(self.store.settings.get('selectedVersion',''))
        if not re.fullmatch(r'[A-Za-z0-9_.+\-]+',version):return
        self._catalog_generation+=1;generation=self._catalog_generation
        self._installer={'minecraft':version,'rows':[{'kind':k,'title':title,'status':'正在获取版本列表…','choices':[],'loading':True} for k,title in COMPONENTS]};self.installerChanged.emit()
        catalog=InstallerCatalog(self.engine)
        for kind,title in COMPONENTS:self.submit(f'component-{generation}-{kind}',lambda kind=kind:catalog.choices(kind,version))
    def _catalog_result(self,key,choices,error):
        _,generation,kind=key.split('-',2)
        if int(generation)!=self._catalog_generation:return
        for row in self._installer['rows']:
            if row['kind']==kind:row.update(choices=choices,loading=False,status='获取失败，点击重试' if error else ('可以选择' if choices else '此游戏版本暂无可用组件'))
        self.installerChanged.emit()
    @Slot('QVariantMap')
    def installPlan(self,plan):
        try:
            version,loader,chosen=validate_plan(plan)
            self.submit('install-'+version,lambda:InstallerCatalog(self.engine).install(dict(plan)),True)
        except Exception as exc:self.message.emit('无法安装',str(exc))
    @Slot()
    def repairVersion(self):
        version=self.store.settings.get('selectedVersion')
        if not version:self.message.emit('尚未选择版本','请先在版本管理中选择一个版本。');return
        self.submit('install-'+version,lambda:self.engine.install(version,repair=True),True)
    @Slot()
    def launch(self):self.launchServer('')
    @Slot(str)
    def launchServer(self,server):
        if self._runtime['running']:self.message.emit('游戏正在运行','请先退出当前游戏。');return
        version=self.store.settings.get('selectedVersion')
        account=dict(self.account());game=self.store.game_dir()
        if not version:self.message.emit('请先安装游戏','打开版本管理，安装并选择一个版本后再启动。');return
        if not account:self.message.emit('请先添加账号','你可以登录微软正版账号，或添加本地离线账号。');return
        def job():
            nonlocal account
            if account.get('kind')=='microsoft' and account.get('expires_at',0)<time.time()+120:
                account=Auth(self.cancel).refresh(account)
                self.accounts=[a for a in self.accounts if a['id']!=account['id']]+[account];self.vault.write(self.accounts)
            return self.engine.launch(version,account,game,self._exited.emit,server)
        self.submit('launch',job,True)
    @Slot()
    def stopGame(self):self.engine.stop()
    @Slot(str,str)
    def searchMods(self,query,kind='mod'):
        self._search_id+=1;ident=self._search_id;self._results=[];self.dataChanged.emit()
        self.submit(f'search-{ident}',lambda:Modrinth(self.engine).search(query,kind))
    @Slot(str,str)
    def installMod(self,project,kind='mod'):
        if self._runtime['running']:self.message.emit('请先退出游戏','安装资源或修改模组前，请先退出当前实例。');return
        self.submit('install-mod',lambda:Modrinth(self.engine).install(project,kind),True)
    @Slot(str)
    def listFiles(self,kind='mods'):
        if kind not in ('mods','resourcepacks','shaderpacks','screenshots','saves'):return
        self._filekind=kind;folder=self.store.game_dir()/kind;folder.mkdir(exist_ok=True)
        self._files=[{'name':p.name,'size':round(p.stat().st_size/1048576,2),'enabled':not p.name.endswith('.disabled'),'directory':p.is_dir()} for p in sorted(folder.iterdir()) if not p.name.startswith('.')]
        self.dataChanged.emit()
    @Slot(str)
    def toggleMod(self,name):
        if self._runtime['running'] or self._runtime['busy']:return
        try:
            root=self.store.game_dir()/'mods';p=safe_path(root,name)
            if p.suffix=='.jar':dest=p.with_name(p.name+'.disabled')
            elif p.name.endswith('.jar.disabled'):dest=p.with_name(p.name[:-9])
            else:return
            if dest.exists():raise ValueError('目标文件已存在')
            p.rename(dest);self.listFiles('mods')
        except Exception as e:self.message.emit('操作失败',str(e))
    @Slot(str)
    def createInstance(self,name):
        if self._runtime['busy']:return
        try:self.store.create_instance(name,self.store.settings.get('selectedVersion',''));self.refresh();self.settingsChanged.emit()
        except Exception as e:self.message.emit('无法创建',str(e))
    @Slot(str)
    def selectInstance(self,ident):
        if self._runtime['busy'] or self._runtime['running']:return
        x=next((x for x in self.store.instances if x['id']==ident),None)
        if x:self.store.settings.update(selectedInstance=ident,selectedVersion=x.get('version',''));self.store.save();self.refresh();self.settingsChanged.emit()
    @Slot(str)
    def saveNotes(self,notes):self.store.instance()['notes']=notes[:32000];self.store.save()
    @Property(str,notify=dataChanged)
    def instanceNotes(self):return self.store.instance().get('notes','')
    @Slot(str)
    def chooseFile(self,kind):
        if kind=='java':
            path,_=QFileDialog.getOpenFileName(None,'选择 Java 可执行文件','','Java (java.exe javaw.exe);;所有文件 (*)')
            if path:self.setSetting('java',path)
        elif kind=='skin':
            path,_=QFileDialog.getOpenFileName(None,'选择 64×64 Minecraft 皮肤','','PNG 图片 (*.png)')
            if path:
                from PySide6.QtGui import QImage
                img=QImage(path)
                if img.isNull() or img.width() not in (64,128,256,512,1024) or img.height() not in (img.width(),img.width()//2):self.message.emit('皮肤无效','请选择 Minecraft 格式的 PNG 皮肤。');return
                dest=self.store.root/'skins'/('custom-'+__import__('hashlib').sha256(Path(path).read_bytes()).hexdigest()+'.png');dest.parent.mkdir(exist_ok=True);shutil.copyfile(path,dest);self.store.settings.update(skinMode='custom',customSkin=str(dest));self.store.save();self._sync_skin(force=True)
        elif kind=='pack':
            path,_=QFileDialog.getOpenFileName(None,'导入 Modrinth 整合包','','Modrinth 整合包 (*.mrpack)')
            if path:self.submit('import-pack',lambda:Modrinth(self.engine).import_pack(path),True)
        elif kind=='library':
            path=QFileDialog.getExistingDirectory(None,'选择含 versions / assets / libraries 的游戏目录')
            if path and not self._runtime['busy']:
                self.setSetting('library',path);self.engine=Engine(self.store,self._progress.emit,self._line.emit,self.cancel);self.terra.e=self.engine;self.refresh()
        elif kind in ('mod','resourcepack','shader'):
            path,_=QFileDialog.getOpenFileName(None,'导入本地资源','','资源文件 (*.jar *.zip)')
            if path and not self._runtime['running']:
                folder=self.store.game_dir()/({'mod':'mods','resourcepack':'resourcepacks','shader':'shaderpacks'}[kind]);folder.mkdir(exist_ok=True);shutil.copyfile(path,folder/Path(path).name);self.listFiles(folder.name)
    @Slot(str)
    def openFolder(self,kind):
        mapping={'game':self.store.game_dir(),'library':self.store.library,'logs':self.store.root/'logs','downloads':self.store.root/'downloads','backups':self.store.root/'backups'}
        path=mapping.get(kind,self.store.game_dir()/kind)
        if kind not in (*mapping,'mods','resourcepacks','shaderpacks','saves','screenshots'):return
        path.mkdir(parents=True,exist_ok=True);QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    @Slot(str)
    def openLink(self,kind):
        urls={'project':PROJECT,'mobile':MOBILE_PROJECT,'sponsor':SPONSOR,'zl2':'https://github.com/ZalithLauncher/ZalithLauncher2','terracotta':'https://github.com/burningtnt/Terracotta','license':str(self.assets/'THIRD_PARTY_NOTICES.txt')}
        if kind=='license':QDesktopServices.openUrl(QUrl.fromLocalFile(urls[kind]))
        elif kind in urls:QDesktopServices.openUrl(QUrl(urls[kind]))
    @Slot()
    def exportLogs(self):
        path,_=QFileDialog.getSaveFileName(None,'导出已脱敏日志','AuroraLauncher-log.txt','文本文件 (*.txt)')
        if path:Path(path).write_text(redact(self.logText),encoding='utf-8');self.message.emit('已导出',path)
    @Slot()
    def preflight(self):
        version=self.store.settings.get('selectedVersion','');account=self.account()
        self._diagnostics=[{'name':'游戏版本','detail':version or '尚未选择','ok':bool(version and self.engine.metadata(version))},{'name':'账号','detail':account.get('name','尚未添加'),'ok':bool(account)},{'name':'内存','detail':str(self.store.settings['memory'])+' MiB','ok':True},{'name':'实例隔离','detail':str(self.store.game_dir()),'ok':True},{'name':'微软 Client ID','detail':CLIENT_ID,'ok':True},{'name':'Java','detail':self.store.settings.get('java') or '按游戏版本自动检测 / 安装','ok':True}];self.dataChanged.emit()
    @Slot()
    def networkDiagnostics(self):
        def job():
            endpoints=[('Minecraft 版本','https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'),('BMCLAPI 备用源','https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json'),('Modrinth','https://api.modrinth.com/v2/tag/loader'),('GitHub 发布','https://api.github.com/repos/reunionSama/AuroraLauncher/releases?per_page=1')]
            def probe(item):
                name,url=item;start=time.monotonic()
                try:
                    with self.engine.net.session().get(url,timeout=(4,6),stream=True) as r:return {'name':name,'detail':f'HTTP {r.status_code} · {round((time.monotonic()-start)*1000)} ms','ok':r.status_code==200}
                except Exception:return {'name':name,'detail':'连接超时或网络不可达','ok':False}
            with ThreadPoolExecutor(max_workers=4) as ex:return list(ex.map(probe,endpoints))
        self.submit('diagnostics',job)
    @Slot()
    def scanJava(self):
        def job():
            candidates=set()
            for path in [shutil.which('java'),self.store.settings.get('java')]:
                if path:candidates.add(str(path))
            for env in ('JAVA_HOME','JDK_HOME'):
                if os.environ.get(env):candidates.add(str(Path(os.environ[env])/'bin'/('java.exe' if sys.platform=='win32' else 'java')))
            for root in [self.store.library/'runtime',Path(os.environ.get('ProgramFiles','/nonexistent'))/'Java',Path(os.environ.get('ProgramFiles','/nonexistent'))/'Eclipse Adoptium',Path(os.environ.get('ProgramFiles','/nonexistent'))/'Microsoft']:
                if root.exists():candidates.update(str(p) for p in root.glob('**/bin/java.exe'))
            values=[]
            for p in sorted(candidates):
                try:
                    r=subprocess.run([p,'-version'],capture_output=True,text=True,timeout=6,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
                    if r.returncode==0:values.append({'path':p,'description':(r.stderr or r.stdout).splitlines()[0]})
                except Exception:pass
            return values
        self.submit('scan-java',job)
    @Slot(str)
    def backupWorld(self,name):
        root=self.store.game_dir()/'saves';world=safe_path(root,name)
        if not world.is_dir():return
        def job():
            folder=self.store.root/'backups';folder.mkdir(exist_ok=True);dest=folder/(re.sub(r'[^\w.-]','_',name)+'-'+time.strftime('%Y%m%d-%H%M%S')+'.zip')
            with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
                for p in world.rglob('*'):
                    self.engine.net.check()
                    if p.is_file() and not p.is_symlink():z.write(p,p.relative_to(world))
            return str(dest)
        self.submit('backup',job,True)
    @Slot()
    def restoreWorld(self):
        path,_=QFileDialog.getOpenFileName(None,'恢复存档到新目录','','ZIP 存档备份 (*.zip)')
        if not path:return
        def job():
            dest=self.store.game_dir()/'saves'/('恢复-'+time.strftime('%Y%m%d-%H%M%S'));self.engine.extract_zip(path,dest);return str(dest)
        self.submit('restore',job,True)
    @Slot()
    def exportInstance(self):
        path,_=QFileDialog.getSaveFileName(None,'导出当前实例',self.store.instance()['name']+'.zip','Aurora 实例备份 (*.zip)')
        if not path:return
        root=self.store.game_dir();info=dict(self.store.instance())
        def job():
            with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
                z.writestr('aurora-instance.json',json.dumps(info,ensure_ascii=False))
                for p in root.rglob('*'):
                    self.engine.net.check()
                    if p.is_file() and not p.is_symlink() and p.relative_to(root).parts[0] not in ('logs','crash-reports'):z.write(p,'game/'+p.relative_to(root).as_posix())
            return path
        self.submit('export-instance',job,True)
    @Slot()
    def importInstance(self):
        path,_=QFileDialog.getOpenFileName(None,'导入 Aurora 实例','','Aurora 实例备份 (*.zip)')
        if not path:return
        def job():
            ident=uuid.uuid4().hex;stage=self.store.root/'instances'/(ident+'.stage')
            try:
                self.engine.extract_zip(path,stage);meta=load_json(stage/'aurora-instance.json',{})
                if not (stage/'game').is_dir() or not meta.get('name'):raise ValueError('这不是 Aurora 实例备份')
                version=meta.get('version','')
                if version:self.engine.install(version)
                meta['id']=ident;os.replace(stage,self.store.root/'instances'/ident);self.store.instances.append(meta);self.store.settings.update(selectedInstance=ident,selectedVersion=version);self.store.save();return '实例已导入：'+meta['name']
            except Exception:shutil.rmtree(stage,ignore_errors=True);raise
        self.submit('import-pack',job,True)
    @Slot(str,str)
    def terraAction(self,action,room=''):
        player=self.account().get('name','AuroraPlayer')
        fn={'host':lambda:self.terra.host(player),'join':lambda:self.terra.join(room,player),'leave':self.terra.leave}.get(action)
        if fn:self.submit('terra-'+action,fn,True)
    def _poll_terra(self):
        if self.terra.port and not self._runtime['busy']:self.submit('terra-poll',self.terra.state)
    def _show_terra(self,state):
        self._terra_failures=0
        session=state.get('_session','')
        if session!=self._terra_session:self._terra_session=session;self._terra_index=-1
        index=state.get('index',self._terra_index+1)
        if index<=self._terra_index:return
        self._terra_index=index
        names={'waiting':'待机','host-scanning':'请进入存档并对局域网开放','host-starting':'正在创建房间','host-ok':'房间已就绪','guest-connecting':'正在连接房主','guest-starting':'正在建立连接','guest-ok':'已加入房间','exception':'连接中断，请离开后重试'}
        self._set(room=state.get('room',''),roomState=names.get(state.get('state'),state.get('state','未知状态')),roomAddress=state.get('url',''),roomMembers=state.get('profiles',[]))
    @Slot(bool)
    def checkUpdate(self,manual=True):
        if any(k in self._jobs for k in ('update-manual','update-auto')):return
        self.submit('update-manual' if manual else 'update-auto',lambda:self.updater.check(manual))
    @Slot()
    def downloadUpdate(self):
        if not self._updates:return
        value=dict(self._updates)
        self.submit('download-update',lambda:self.engine.net.download(value['url'],self.store.root/'downloads'/('AuroraLauncher-'+value['version']+'.exe'),value['digest'],'sha256',value['size'],lambda n,t:self._progress.emit('下载 Windows 新版',n,t)),True)
    @Slot()
    def refresh(self):
        self._local=self.engine.local_versions();selected=self.store.settings.get('selectedVersion','')
        if selected and not any(v['id']==selected for v in self._local):self.store.settings['selectedVersion']=''
        if not self.store.settings.get('selectedVersion') and self._local:self.store.settings['selectedVersion']=self._local[0]['id'];self.store.instance()['version']=self._local[0]['id']
        self.listFiles(self._filekind);saves=self.store.game_dir()/'saves';saves.mkdir(exist_ok=True)
        self._worlds=[{'name':p.name,'path':str(p)} for p in saves.iterdir() if p.is_dir()]
        self._sync_skin()
        self.store.save();self.dataChanged.emit();self.settingsChanged.emit()
    def _skin_key(self):
        account=self.account()
        return (account.get('id',''),account.get('skin',''),account.get('skin_model','classic'),account.get('cape',''),self.store.settings.get('customSkin',''),self.store.settings.get('skinMode','account'))
    def _sync_skin(self,force=False):
        identity=self._skin_key()
        if identity==self._skin_identity and not force:return
        self._skin_identity=identity;self._skin_generation+=1;self._skin=str(self.assets/'aurora_skin.png');self._skin_model='classic';self._cape=''
        cached_cape=self.skins.cached(self.account().get('cape',''))
        if cached_cape:self._cape=str(cached_cape)
        custom=Path(self.store.settings.get('customSkin') or self.store.root/'custom_skin.png');account=dict(self.account())
        if identity[-1]=='custom' and custom.exists():
            self._skin=str(custom);self._skin_status='自定义皮肤';self.dataChanged.emit();return
        if account.get('kind')!='microsoft':self._skin_status='离线账号 · 可导入自定义皮肤';self.dataChanged.emit();return
        cached=self.skins.cached(account.get('skin',''))
        if cached:self._skin=str(cached);self._skin_model=account.get('skin_model','classic')
        self._skin_status='正在同步玩家皮肤…';self.dataChanged.emit()
        self.submit(f'skin-{self._skin_generation}',lambda:self.skins.resolve(account))
    @Slot()
    def useAccountSkin(self):
        self.store.settings['skinMode']='account';self.store.save();self._sync_skin(force=True);self.settingsChanged.emit()
    def close(self):
        self.store.save();self.cancel.set();self._skin_cancel.set();self.pool.shutdown(wait=False,cancel_futures=True);self.catalog_pool.shutdown(wait=False,cancel_futures=True);self._logfile.flush();self._logfile.close()

