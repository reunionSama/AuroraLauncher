# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded, asynchronous project-icon downloads; the QML thread never does I/O."""
import hashlib,os,time
from pathlib import Path
from urllib.parse import urlparse
from PySide6.QtGui import QImage
from .storage import atomic_json,load_json

class IconCache:
    def __init__(self,net):
        self.net=net;self.root=net.cache/'project-icons';self.root.mkdir(exist_ok=True)
    def path(self,url):
        return self.root/(hashlib.sha256(url.encode()).hexdigest()+'.png')
    def cached(self,url):
        if not url:return ''
        p=self.path(url)
        return p.as_uri() if p.is_file() else ''
    def fetch(self,url):
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname!='cdn.modrinth.com' or parsed.username or parsed.password:return ''
        path=self.path(url)
        if path.exists():return path.as_uri()
        try:
            with self.net.session().get(url,timeout=(4,8),stream=True) as response:
                response.raise_for_status();data=bytearray()
                for chunk in response.iter_content(32768):
                    self.net.check();data.extend(chunk)
                    if len(data)>2*1024*1024:return ''
            image=QImage.fromData(bytes(data))
            if image.isNull() or max(image.width(),image.height())>4096:return ''
            image=image.scaled(96,96,aspectMode=__import__('PySide6.QtCore',fromlist=['Qt']).Qt.AspectRatioMode.KeepAspectRatio)
            temp=path.with_suffix('.tmp')
            if image.save(str(temp),'PNG'):os.replace(temp,path)
            self.trim()
            return path.as_uri() if path.exists() else ''
        except Exception:return ''
    def trim(self):
        # At most a few MiB for decoded thumbnails across sessions.
        files=sorted(self.root.glob('*.png'),key=lambda p:p.stat().st_mtime,reverse=True)
        for p in files[256:]:
            try:p.unlink()
            except OSError:pass
