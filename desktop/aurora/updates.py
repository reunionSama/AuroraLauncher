# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Pinned release channel, conditional requests and a rate-limit-free HTML fallback."""
import html,re,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html.parser import HTMLParser
import requests
from . import PROJECT,VERSION,BUILD_RELEASED_AT,USER_AGENT
from .storage import load_json,atomic_json

RELEASE_URL=PROJECT+'/releases/tag/publicLauncher'
ASSETS_URL=PROJECT+'/releases/expanded_assets/publicLauncher'
API_URL='https://api.github.com/repos/reunionSama/AuroraLauncher/releases/tags/publicLauncher'

class BodyParser(HTMLParser):
    def __init__(self):super().__init__();self.depth=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        attr=dict(attrs)
        if tag=='div' and 'markdown-body' in attr.get('class','').split() and not self.depth:self.depth=1
        elif self.depth and tag=='div':self.depth+=1
        if self.depth and tag in ('br','p','li','h1','h2','h3','pre'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if self.depth and tag=='div':self.depth-=1
        elif self.depth and tag in ('p','li','h1','h2','h3','pre'):self.parts.append('\n')
    def handle_data(self,data):
        if self.depth:self.parts.append(data)

def parse_web(release_html,assets_html):
    parser=BodyParser();parser.feed(release_html);body=re.sub(r'\n{3,}','\n\n',''.join(parser.parts)).strip()
    assets=[];prefix='/reunionSama/AuroraLauncher/releases/download/publicLauncher/'
    for row in re.findall(r'<li\b[^>]*>(.*?)</li>',assets_html,re.S|re.I):
        link=re.search(r'href="('+re.escape(prefix)+r'[^"<>]+)"',row)
        if not link:continue
        path=html.unescape(link[1]);name=path.rsplit('/',1)[-1]
        digest=re.search(r'sha256:([a-fA-F0-9]{64})',row);stamp=re.search(r'<relative-time[^>]+datetime="([^"]+)"',row)
        assets.append({'name':name,'browser_download_url':'https://github.com'+path,'digest':'sha256:'+digest[1] if digest else '', 'updated_at':stamp[1] if stamp else '', 'size':0})
    if not body or not assets:raise ValueError('发布页暂时无法解析')
    return {'name':'AuroraLauncher · publicLauncher','tag_name':'publicLauncher','body':body,'assets':assets}

def newer_asset(release):
    declared=re.findall(r'(?i)\bv(\d+)\.(\d+)\.(\d+)\b',(release.get('name','') or '')+'\n'+(release.get('body','') or ''))
    if declared and max(tuple(map(int,v)) for v in declared)<=tuple(map(int,VERSION.split('.'))):return None
    baseline=datetime.fromisoformat(BUILD_RELEASED_AT.replace('Z','+00:00'))
    for asset in release.get('assets',[]):
        if asset.get('name')!='AuroraLauncher.exe':continue
        url=asset.get('browser_download_url','');digest=asset.get('digest','')
        if url!=PROJECT+'/releases/download/publicLauncher/AuroraLauncher.exe':continue
        try:stamp=datetime.fromisoformat(asset.get('updated_at','').replace('Z','+00:00'))
        except ValueError:continue
        if stamp<=baseline:continue
        if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest):raise ValueError('新版未提供 SHA-256，请稍后重试检查更新')
        return {'title':release.get('name') or 'AuroraLauncher 更新','body':release.get('body') or '发布者未填写更新说明','url':url,'digest':digest[7:].lower(),'size':asset.get('size',0),'version':stamp.strftime('%Y%m%d-%H%M%S')}
    return None

class UpdateChecker:
    def __init__(self,root,session=None):
        self.file=root/'desktop-release.json';self.session=session
    def _get(self,url,headers=None):
        session=self.session or requests.Session()
        try:
            with session.get(url,headers={'User-Agent':USER_AGENT,**(headers or {})},timeout=(5,9),stream=True) as response:
                if response.status_code in (304,403,429):return response.status_code,dict(response.headers),''
                response.raise_for_status();data=bytearray()
                for chunk in response.iter_content(32768):
                    data.extend(chunk)
                    if len(data)>3*1024*1024:raise ValueError('发布信息过大')
                return response.status_code,dict(response.headers),data.decode('utf-8')
        finally:
            if self.session is None:session.close()
    def check(self,manual=False):
        now=time.time();saved=load_json(self.file,{});cached=saved.get('release');source='GitHub API'
        if cached and now-saved.get('checked_at',0)<(45 if manual else 900):return self._result(cached,'最近检查缓存',saved['checked_at'])
        release=None
        if now>=saved.get('api_retry_at',0):
            try:
                status,headers,data=self._get(API_URL,{'If-None-Match':saved['etag']} if saved.get('etag') else {})
                if status==304 and cached:release=cached
                elif status in (403,429):
                    saved['api_retry_at']=max(now+300,min(now+86400,float(headers.get('X-RateLimit-Reset',now+3600))))
                else:
                    import json
                    release=json.loads(data)
                    if release.get('tag_name')!='publicLauncher' or release.get('draft'):raise ValueError('发布渠道不匹配')
                    saved['etag']=headers.get('ETag','')
            except (requests.RequestException,ValueError,KeyError):pass
        if release is None:
            source='GitHub 发布页备用通道'
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures=[pool.submit(self._get,u) for u in (RELEASE_URL,ASSETS_URL)]
                    pages=[f.result() for f in futures]
                if any(p[0]!=200 for p in pages):raise ValueError('发布页暂时不可访问')
                release=parse_web(pages[0][2],pages[1][2])
            except (requests.RequestException,ValueError):
                atomic_json(self.file,saved)
                if cached and now-saved.get('checked_at',0)<86400:return self._result(cached,'离线缓存（本次未能联网，不能确认是否最新）',saved['checked_at'],True)
                raise RuntimeError('GitHub 暂时限流或网络不可达，发布页备用通道也未能连接，请稍后再试。')
        saved.update(release=release,checked_at=now);atomic_json(self.file,saved)
        return self._result(release,source,now)
    @staticmethod
    def _result(release,source,checked_at,stale=False):
        candidate=newer_asset(release)
        return {'candidate':candidate,'source':source,'checked_at':checked_at,'stale':stale,'body':release.get('body',''),'message':('本次未能联网，仅显示上次检查结果。' if stale else ('发现新版。' if candidate else '发布页暂无比当前 '+VERSION+' 更新的 Windows 文件。'))+'\n检查渠道：publicLauncher\n'+source}
