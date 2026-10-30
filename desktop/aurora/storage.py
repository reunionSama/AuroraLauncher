# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import base64, ctypes, json, os, re, sys, uuid, threading, time
from pathlib import Path, PurePosixPath

DEFAULTS = dict(memory=4096, width=1280, height=720, workers=12, source="auto", java="", library="", sky=True, actions=True, interval=15, brightness=0.72, speed=0.5, hue=0.4, fps=60, theme="dark", autoUpdate=True, jvmArgs="", selectedAccount="", selectedVersion="", selectedInstance="default", closeOnLaunch=False, language="zh_CN")

_json_lock=threading.RLock()
def atomic_json(path:Path, value):
    # Windows cannot always replace the same pathname concurrently. Serialize our
    # writers, then tolerate a brief antivirus/indexer lock without losing old data.
    with _json_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
        try:
            with temp.open("w",encoding="utf-8") as f:
                json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
            for attempt in range(7):
                try:os.replace(temp,path);break
                except PermissionError:
                    if attempt==6:raise
                    time.sleep(.015*(2**attempt))
        finally:temp.unlink(missing_ok=True)

def load_json(path:Path, default):
    try:return json.loads(path.read_text("utf-8"))
    except (OSError,ValueError):return default

def safe_path(root:Path,name:str)->Path:
    # Apply Windows rules on every host, so a pack cannot become unsafe after transfer.
    if not isinstance(name,str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("文件路径不安全")
    p=PurePosixPath(name)
    reserved={"con","prn","aux","nul",*("com"+str(i) for i in range(1,10)),*("lpt"+str(i) for i in range(1,10))}
    if p.is_absolute() or any(x in {".",".."} or x.endswith((" ",".")) or x.split('.')[0].lower() in reserved for x in p.parts):
        raise ValueError("文件路径不安全")
    out=root.joinpath(*p.parts).resolve()
    if not out.is_relative_to(root.resolve()):raise ValueError("文件越过了目标目录")
    return out

class Store:
    def __init__(self,root:Path|None=None):
        base=Path(os.environ.get("LOCALAPPDATA",str(Path.home()/".local/share")))
        self.root=(root or Path(os.environ.get("AURORA_HOME",str(base/"AuroraLauncher"/"Desktop6")))).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.file=self.root/"settings.json"
        self.settings={**DEFAULTS,**load_json(self.file,{})}
        self.settings["memory"]=max(512,min(65536,int(self.settings["memory"])))
        self.settings["workers"]=max(2,min(32,int(self.settings["workers"])))
        self.settings["interval"]=max(5,min(60,int(self.settings["interval"])))
        self.instances=load_json(self.root/"instances.json",[{"id":"default","name":"默认实例","version":"","notes":""}])
        if not self.instances:self.instances=[{"id":"default","name":"默认实例","version":"","notes":""}]
        for d in ["logs","cache","downloads","instances"]:(self.root/d).mkdir(exist_ok=True)
    @property
    def library(self):return Path(self.settings.get("library") or self.root/"minecraft").resolve()
    def save(self):atomic_json(self.file,self.settings);atomic_json(self.root/"instances.json",self.instances)
    def instance(self):return next((x for x in self.instances if x['id']==self.settings["selectedInstance"]),self.instances[0])
    def game_dir(self,instance=None):
        x=instance or self.instance()
        p=self.root/"instances"/x["id"]/"game";p.mkdir(parents=True,exist_ok=True);return p
    def create_instance(self,name,version=""):
        name=name.strip()
        if not name:raise ValueError("请输入实例名称")
        obj={"id":uuid.uuid4().hex,"name":name[:80],"version":version,"notes":""}
        self.instances.append(obj);self.settings["selectedInstance"]=obj["id"];self.save();return obj

class Vault:
    """Windows DPAPI: secrets are bound to the current Windows account, never plain JSON."""
    def __init__(self,root:Path):self.root=root;self.path=root/"accounts.enc"
    def _crypt(self,data:bytes,encrypt:bool):
        if sys.platform=="win32":
            from ctypes import wintypes
            class Blob(ctypes.Structure):_fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_ubyte))]
            buf=(ctypes.c_ubyte*len(data)).from_buffer_copy(data);src=Blob(len(data),buf);out=Blob()
            fn=ctypes.windll.crypt32.CryptProtectData if encrypt else ctypes.windll.crypt32.CryptUnprotectData
            if not fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(out)):raise OSError("Windows 无法解密此账号，请重新登录")
            try:return ctypes.string_at(out.pbData,out.cbData)
            finally:ctypes.windll.kernel32.LocalFree(out.pbData)
        from cryptography.fernet import Fernet
        key=self.root/".vault-key"
        if not key.exists():
            fd=os.open(key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"wb") as f:f.write(Fernet.generate_key())
        f=Fernet(key.read_bytes());return f.encrypt(data) if encrypt else f.decrypt(data)
    def read(self):
        if not self.path.exists():return []
        return json.loads(self._crypt(self.path.read_bytes(),False))
    def write(self,accounts):
        tmp=self.path.with_suffix(".tmp");tmp.write_bytes(self._crypt(json.dumps(accounts).encode(),True));os.chmod(tmp,0o600);os.replace(tmp,self.path)

def redact(text:str)->str:
    text=re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9_.~+/=-]+',r'\1[已隐藏]',text)
    text=re.sub(r'(?i)((?:access[_-]?token|refresh[_-]?token|client_secret|authorization|--uuid)\s*["\s:=]+)[^\s",}]+',r'\1[已隐藏]',text)
    text=re.sub(r'(?i)(--accessToken\s+)\S+',r'\1[已隐藏]',text)
    return text
