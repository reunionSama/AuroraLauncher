# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Unmodified Terracotta process + documented loopback HTTP interface."""
import json,os,shutil,subprocess,sys,tarfile,time,uuid
from pathlib import Path
from .storage import safe_path

TERRA_VERSION='0.4.2'
TERRA_WIN='https://github.com/burningtnt/Terracotta/releases/download/v0.4.2/terracotta-0.4.2-windows-x86_64-pkg.tar.gz'
TERRA_SHA256='07ebe139e3ca5f74576e58b1a96efe59abdfbe148d3f1a49bfdca8b6f70745f0'
class Terracotta:
    def __init__(self,engine):self.e=engine;self.port=0;self.process=None;self.session=uuid.uuid4().hex
    def ensure(self):
        if self.port:
            try:self.state();return
            except Exception:self.port=0
        if sys.platform!='win32':raise RuntimeError("此构建的陶瓦组件面向 Windows；请使用官方对应平台发行包")
        root=self.e.store.root/'tools'/'terracotta';exe=next(root.rglob('terracotta.exe'),None) if root.exists() else None
        if not exe:
            self.e.emit('正在下载官方陶瓦联机组件')
            archive=self.e.store.root/'downloads'/'terracotta-0.4.2.tar.gz'
            self.e.net.download(TERRA_WIN,archive,TERRA_SHA256,'sha256')
            root.mkdir(parents=True,exist_ok=True)
            with tarfile.open(archive,'r:gz') as tar:
                if sum(m.size for m in tar.getmembers())>1024**3:raise ValueError('陶瓦组件解压体积异常')
                for member in tar.getmembers():
                    if member.name in ('.','./'):continue
                    p=safe_path(root,member.name.removeprefix('./'))
                    if member.issym() or member.islnk():raise ValueError('组件包含不安全链接')
                    if member.isdir():p.mkdir(parents=True,exist_ok=True)
                    elif member.isfile():
                        p.parent.mkdir(parents=True,exist_ok=True)
                        with tar.extractfile(member) as src,p.open('wb') as out:shutil.copyfileobj(src,out)
            exe=next(root.rglob('terracotta.exe'),None)
        if not exe:raise RuntimeError('没有找到陶瓦可执行文件')
        self.session=uuid.uuid4().hex
        portfile=self.e.store.root/'cache'/('terra-'+uuid.uuid4().hex+'.json')
        flags=subprocess.CREATE_NO_WINDOW
        self.process=subprocess.Popen([str(exe),'--hmcl',str(portfile)],cwd=exe.parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
        for _ in range(100):
            self.e.net.check()
            if portfile.exists():
                try:
                    self.port=int(json.loads(portfile.read_text())['port'])
                    if not 1024<=self.port<=65535:raise ValueError('端口无效')
                    self.state();return
                finally:portfile.unlink(missing_ok=True)
            time.sleep(.15)
        raise RuntimeError('陶瓦启动超时，请重试或检查 Windows 防火墙提示')
    def call(self,path,params=None):
        if not self.port:raise RuntimeError('请先启动陶瓦联机')
        r=self.e.net.session().get(f'http://127.0.0.1:{self.port}'+path,params=params,timeout=(2,4));r.raise_for_status();return r
    def state(self):
        value=self.call('/state').json();value['_session']=self.session;return value
    def host(self,player):self.ensure();self.call('/state/ide');self.call('/state/scanning',{'player':player});return self.state()
    def join(self,room,player):
        if not room.strip():raise ValueError('请输入房间邀请码')
        self.ensure();self.call('/state/ide');self.call('/state/guesting',{'room':room.strip(),'player':player});return self.state()
    def leave(self):
        if self.port:self.call('/state/ide')
        return self.state() if self.port else {'state':'waiting'}
