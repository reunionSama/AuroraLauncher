# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Official account textures with bounded downloads and an immutable disk cache."""
import hashlib,os,re,threading,uuid
from pathlib import Path
from urllib.parse import urlsplit
import requests
from PySide6.QtGui import QImageReader
from PySide6.QtCore import QByteArray,QBuffer,QIODevice
from . import USER_AGENT
from .auth import profile_skin

MAX_SKIN_BYTES=2*1024*1024

def texture_url(url):
    parsed=urlsplit(url)
    if parsed.scheme not in ('https','http') or parsed.netloc.lower()!='textures.minecraft.net' or not re.fullmatch(r'/texture/[a-fA-F0-9]{32,128}',parsed.path) or parsed.query or parsed.fragment:
        raise ValueError('玩家皮肤地址不是 Minecraft 官方材质地址')
    return 'https://textures.minecraft.net'+parsed.path

def validate_skin(data):
    if len(data)>MAX_SKIN_BYTES or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('皮肤不是有效的 PNG 图片')
    buffer=QBuffer();buffer.setData(QByteArray(data));buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader=QImageReader(buffer,b'png');size=reader.size()
    if size.width() not in (64,128,256,512,1024) or size.height() not in (size.width(),size.width()//2):
        raise ValueError('玩家皮肤尺寸不符合 Minecraft 格式')
    image=reader.read()
    if image.isNull():raise ValueError('玩家皮肤图片损坏')
    return image

class SkinCache:
    def __init__(self,root,cancel=None,session=None):
        self.root=Path(root)/'skins';self.root.mkdir(parents=True,exist_ok=True)
        self.cancel=cancel or threading.Event();self.session=session
    def cached(self,url):
        if not url:return None
        try:
            path=self.root/(hashlib.sha256(texture_url(url).encode()).hexdigest()+'.png')
            if path.is_file():validate_skin(path.read_bytes());return path
        except (OSError,ValueError):pass
        return None
    def resolve(self,account,refresh_profile=True):
        session=self.session or requests.Session();session.headers.update({'User-Agent':USER_AGENT})
        owned=self.session is None;meta={k:account[k] for k in ('skin','skin_model','cape','cape_id') if k in account};warning=''
        try:
            if refresh_profile and account.get('access_token'):
                try:
                    with session.get('https://api.minecraftservices.com/minecraft/profile',headers={'Authorization':'Bearer '+account['access_token']},timeout=(5,10)) as response:
                        response.raise_for_status();profile=response.json()
                    if profile.get('id','').replace('-','')!=account['id'].replace('-',''):raise ValueError('玩家档案与所选账号不一致')
                    meta=profile_skin(profile)
                except (requests.RequestException,ValueError) as exc:
                    warning='未能刷新在线玩家皮肤，已使用该账号缓存；请检查网络或重新登录。'
                    if not meta.get('skin'):raise RuntimeError(warning) from exc
            path=self._download(session,meta.get('skin','')) if meta.get('skin') else ''
            cape_path=''
            if meta.get('cape'):
                try:cape_path=str(self._download(session,meta['cape']))
                except (RuntimeError,ValueError):warning=(warning+' 披风加载失败，可刷新重试。').strip()
            return {'path':str(path),'cape_path':cape_path,'meta':meta,'warning':warning}
        finally:
            if owned:session.close()
    def _download(self,session,url):
            url=texture_url(url);path=self.cached(url)
            if path:return path
            path=self.root/(hashlib.sha256(url.encode()).hexdigest()+'.png');data=bytearray()
            for attempt in range(2):
                if self.cancel.is_set():raise RuntimeError('皮肤加载已取消')
                try:
                    data.clear()
                    with session.get(url,stream=True,allow_redirects=False,timeout=(5,12)) as response:
                        response.raise_for_status()
                        if 300<=response.status_code<400:raise ValueError('皮肤服务返回了意外跳转')
                        if int(response.headers.get('Content-Length',0))>MAX_SKIN_BYTES:raise ValueError('皮肤文件过大')
                        for chunk in response.iter_content(16384):
                            if self.cancel.is_set():raise RuntimeError('皮肤加载已取消')
                            data.extend(chunk)
                            if len(data)>MAX_SKIN_BYTES:raise ValueError('皮肤文件过大')
                    validate_skin(data);break
                except requests.RequestException:
                    if attempt==1:raise RuntimeError('玩家皮肤下载失败，请检查网络后点击刷新皮肤')
                    if self.cancel.wait(.3):raise RuntimeError('皮肤加载已取消')
            temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
            try:temp.write_bytes(data);os.replace(temp,path)
            finally:temp.unlink(missing_ok=True)
            return path

