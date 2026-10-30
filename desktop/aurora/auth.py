# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
import time,uuid,re
import requests
from urllib.parse import urlsplit
from . import CLIENT_ID,USER_AGENT
from .network import Cancelled

TENANT="https://login.microsoftonline.com/consumers/oauth2/v2.0/"
SCOPES="XboxLive.signin offline_access"
DEVICE_LOGIN_URL="https://microsoft.com/link"

def verification_url(device):
    url=device.get('verification_uri',DEVICE_LOGIN_URL)
    parsed=urlsplit(url)
    if parsed.scheme=='https' and parsed.netloc.lower() in ('microsoft.com','www.microsoft.com') and parsed.path.rstrip('/') in ('/link','/devicelogin'):
        return url
    return DEVICE_LOGIN_URL

def profile_skin(profile):
    skin=next((s for s in profile.get('skins',[]) if s.get('state')=='ACTIVE'),{})
    return {'skin':skin.get('url',''),'skin_model':'slim' if skin.get('variant','').upper()=='SLIM' else 'classic'}
class Auth:
    def __init__(self,cancel):
        self.cancel=cancel;self.s=requests.Session();self.s.headers['User-Agent']=USER_AGENT
    def _post(self,url,**kw):
        for attempt in range(3):
            if self.cancel.is_set():raise Cancelled("登录已取消")
            try:
                r=self.s.post(url,timeout=(12,30),**kw)
                if self.cancel.is_set():raise Cancelled("登录已取消")
                if r.status_code<500 or attempt==2:return r
            except requests.RequestException as e:
                if attempt==2:raise RuntimeError("无法连接微软 / Xbox 登录服务，请检查网络后重试") from e
            if self.cancel.wait(.5*(attempt+1)):raise Cancelled("登录已取消")
        raise RuntimeError("登录服务暂时不可用")
    def request(self,url,**kw):
        if self.cancel.is_set():raise Cancelled("登录已取消")
        r=self._post(url,**kw)
        try:body=r.json()
        except ValueError:raise RuntimeError(f"登录接口异常 HTTP {r.status_code}")
        if r.status_code>=400:
            code=body.get('XErr') or body.get('error') or r.status_code
            hints={2148916233:"此微软账号尚未创建 Xbox 玩家档案，请先访问 xbox.com 完成注册。",2148916238:"此账号受到 Xbox 家庭设置限制，请由家庭组织者检查权限。"}
            raise RuntimeError(hints.get(code,f"微软登录失败：{code}。请检查该 client ID 的公开客户端/设备代码配置。"))
        return body
    def start(self):return self.request(TENANT+"devicecode",data={"client_id":CLIENT_ID,"scope":SCOPES})
    def poll(self,device):
        deadline=time.monotonic()+device.get("expires_in",900);interval=max(3,device.get("interval",5))
        while time.monotonic()<deadline:
            if self.cancel.wait(interval):raise Cancelled("登录已取消")
            r=self._post(TENANT+"token",data={"client_id":CLIENT_ID,"grant_type":"urn:ietf:params:oauth:grant-type:device_code","device_code":device["device_code"]})
            body=r.json()
            if r.status_code==200:return self.complete(body)
            error=body.get("error")
            if error=="authorization_pending":continue
            if error=="slow_down":interval+=5;continue
            if error in ("expired_token","authorization_declined","access_denied"):raise RuntimeError("登录已过期或被取消，请重新获取设备码")
            raise RuntimeError("登录轮询失败："+str(error or r.status_code))
        raise RuntimeError("登录码已过期，请重试")
    def refresh(self,account):
        token=self.request(TENANT+"token",data={"client_id":CLIENT_ID,"grant_type":"refresh_token","refresh_token":account['refresh_token'],"scope":SCOPES})
        if not token.get('refresh_token'):token['refresh_token']=account['refresh_token']
        return self.complete(token)
    def complete(self,token):
        xbl=self.request("https://user.auth.xboxlive.com/user/authenticate",json={"Properties":{"AuthMethod":"RPS","SiteName":"user.auth.xboxlive.com","RpsTicket":"d="+token['access_token']},"RelyingParty":"http://auth.xboxlive.com","TokenType":"JWT"})
        xsts=self.request("https://xsts.auth.xboxlive.com/xsts/authorize",json={"Properties":{"SandboxId":"RETAIL","UserTokens":[xbl['Token']]},"RelyingParty":"rp://api.minecraftservices.com/","TokenType":"JWT"})
        uhs=xsts['DisplayClaims']['xui'][0]['uhs']
        minecraft=self.request("https://api.minecraftservices.com/authentication/login_with_xbox",json={"identityToken":f"XBL3.0 x={uhs};{xsts['Token']}"})
        headers={"Authorization":"Bearer "+minecraft['access_token'],"User-Agent":USER_AGENT}
        r=self.s.get("https://api.minecraftservices.com/minecraft/profile",headers=headers,timeout=(8,25))
        if r.status_code==404:raise RuntimeError("登录成功，但此微软账号没有可用的 Minecraft Java 玩家档案")
        if r.status_code>=400:raise RuntimeError(f"Minecraft 玩家信息获取失败：HTTP {r.status_code}")
        profile=r.json()
        return {"id":profile['id'],"uuid":profile['id'],"name":profile['name'],"kind":"microsoft","access_token":minecraft['access_token'],"refresh_token":token.get('refresh_token',''),"expires_at":time.time()+minecraft.get('expires_in',86400),"xuid":xsts['DisplayClaims']['xui'][0].get('xid',''),**profile_skin(profile)}

def offline(name):
    if not re.fullmatch(r"[A-Za-z0-9_]{3,16}",name):raise ValueError("离线名称需为 3–16 位英文字母、数字或下划线")
    raw=bytearray(__import__('hashlib').md5(("OfflinePlayer:"+name).encode()).digest());raw[6]=(raw[6]&15)|48;raw[8]=(raw[8]&63)|128
    ident=uuid.UUID(bytes=bytes(raw)).hex
    return {"id":ident,"uuid":ident,"name":name,"kind":"offline","access_token":"0"}
