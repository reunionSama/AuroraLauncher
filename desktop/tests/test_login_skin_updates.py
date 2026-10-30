import json,threading,time
from pathlib import Path
from unittest.mock import Mock
import pytest,requests
from PySide6.QtCore import QByteArray,QBuffer,QIODevice
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication
from aurora.auth import verification_url,profile_skin
from aurora.skins import SkinCache,texture_url,validate_skin,MAX_SKIN_BYTES
from aurora.updates import UpdateChecker,parse_web,newer_asset,API_URL,RELEASE_URL,ASSETS_URL
from aurora.storage import Store,atomic_json
from aurora.visuals import player_boxes

URL='https://textures.minecraft.net/texture/'+'a'*64
OTHER='https://textures.minecraft.net/texture/'+'b'*64
ASSETS=Path(__file__).resolve().parents[1]/'assets'

@pytest.fixture(scope='module')
def app():
    instance=QApplication.instance() or QApplication([])
    yield instance

@pytest.fixture
def png():
    image=QImage(64,64,QImage.Format.Format_ARGB32);image.fill(QColor('#36bda8'))
    data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly);assert image.save(buffer,'PNG');return bytes(data)

class Response:
    def __init__(self,data=b'',status=200,headers=None,body=None):self.data=data;self.status_code=status;self.headers=headers or {};self.body=body
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError(str(self.status_code))
    def json(self):return self.body
    def iter_content(self,n):yield self.data

class Session:
    def __init__(self,items):self.items=iter(items);self.headers={};self.calls=[]
    def get(self,url,**kwargs):self.calls.append((url,kwargs));return next(self.items)

def test_opens_the_verification_uri_returned_by_microsoft(app,tmp_path,monkeypatch):
    from aurora.bridge import Bridge,QDesktopServices
    bridge=Bridge(Store(tmp_path),ASSETS,True);opened=[]
    monkeypatch.setattr(QDesktopServices,'openUrl',lambda url:opened.append(url.toString()) or True)
    try:
        bridge._on_device('TEST-CODE','https://www.microsoft.com/link');bridge.openLoginPage()
        assert opened==['https://www.microsoft.com/link']
        bridge._set(authUrl='');bridge.openLoginPage();assert opened[-1]=='https://microsoft.com/link'
    finally:bridge.close()

@pytest.mark.parametrize('url',['https://attacker.invalid/link','http://microsoft.com/link','https://microsoft.com@attacker.invalid/link','https://microsoft.com:1234/link'])
def test_verification_link_rejects_external_targets(url):assert verification_url({'verification_uri':url})=='https://microsoft.com/link'

def test_profile_selects_active_skin_and_slim_model():
    assert profile_skin({'skins':[{'state':'INACTIVE','url':OTHER},{'state':'ACTIVE','url':URL,'variant':'SLIM'}]})=={'skin':URL,'skin_model':'slim'}

def test_skin_download_uses_selected_profile_and_cache(tmp_path,png):
    session=Session([Response(body={'id':'123','skins':[{'url':URL,'variant':'SLIM','state':'ACTIVE'}]}),Response(png)])
    cache=SkinCache(tmp_path,session=session);value=cache.resolve({'id':'123','skin':OTHER,'access_token':'test-only'})
    assert value['meta']=={'skin':URL,'skin_model':'slim'} and Path(value['path']).read_bytes()==png
    assert session.calls[0][1]['headers']['Authorization']=='Bearer test-only'
    assert 'headers' not in session.calls[1][1] # Never send the account bearer token to the texture host.
    assert session.calls[1][1]['allow_redirects'] is False
    offline=Session([]);again=SkinCache(tmp_path,session=offline).resolve({'skin':URL},False)
    assert again['path']==value['path'] and offline.calls==[]

def test_expired_profile_uses_own_cache(tmp_path,png):
    SkinCache(tmp_path,session=Session([Response(png)])).resolve({'skin':URL},False)
    value=SkinCache(tmp_path,session=Session([Response(status=401)])).resolve({'id':'123','access_token':'expired','skin':URL})
    assert value['path'] and '缓存' in value['warning'] and value['meta']['skin']==URL

@pytest.mark.parametrize('payload',[b'<html>Bad Gateway</html>',b'\x89PNG\r\n\x1a\n'+b'x'*(MAX_SKIN_BYTES+1)])
def test_invalid_skin_never_enters_cache(tmp_path,payload):
    cache=SkinCache(tmp_path,session=Session([Response(payload)]))
    with pytest.raises(ValueError):cache.resolve({'skin':URL},False)
    assert list(cache.root.iterdir())==[]

def test_redirected_skin_is_not_followed(tmp_path):
    with pytest.raises(ValueError,match='跳转'):SkinCache(tmp_path,session=Session([Response(status=302)])).resolve({'skin':URL},False)

def test_texture_hosts_are_restricted_and_upgraded_to_https():
    assert texture_url(URL.replace('https:','http:'))==URL
    for value in ['https://attacker.invalid/texture/'+'a'*64,URL+'?token=x',URL.replace('minecraft.net','minecraft.net:443')]:
        with pytest.raises(ValueError):texture_url(value)

def test_slim_model_and_second_skin_layer():
    classic=player_boxes('classic');slim=player_boxes('slim')
    assert len(classic)==len(slim)==12
    assert next(b[1][0] for b in slim if b[0]=='leftArm' and not b[-1])==3
    assert next(b[1][0] for b in classic if b[0]=='leftArm' and not b[-1])==4
    assert sum(b[-1] for b in slim)==6

def test_late_skin_result_cannot_replace_newly_selected_account(app,tmp_path):
    from aurora.bridge import Bridge
    bridge=Bridge(Store(tmp_path),ASSETS,True);jobs=[]
    def submit(key,fn,busy=False):bridge._jobs[key]=busy;jobs.append((key,fn))
    bridge.submit=submit
    try:
        bridge.accounts=[{'id':'A','name':'Alice','kind':'microsoft','skin':URL},{'id':'B','name':'Bob','kind':'microsoft','skin':OTHER}]
        bridge.selectAccount('A');first=jobs[-1][0];bridge.selectAccount('B');second=jobs[-1][0]
        bridge._finish(first,{'path':'wrong-account.png','meta':{'skin':URL},'warning':''},'')
        assert bridge.skinPath!='wrong-account.png'
        bridge._finish(second,{'path':'bob.png','meta':{'skin':OTHER,'skin_model':'slim'},'warning':''},'')
        assert bridge.skinPath=='bob.png' and bridge.skinModel=='slim' and 'Bob' in bridge.skinStatus
        bridge.addOffline('OfflineTester');assert bridge.skinPath==str(ASSETS/'aurora_skin.png')
    finally:bridge.close()

def release(stamp='2026-10-31T01:00:00Z'):
    return {'tag_name':'publicLauncher','name':'Aurora','body':'更新说明\n修复问题','assets':[{'name':'AuroraLauncher.exe','browser_download_url':'https://github.com/reunionSama/AuroraLauncher/releases/download/publicLauncher/AuroraLauncher.exe','updated_at':stamp,'digest':'sha256:'+'a'*64,'size':100}]}

def web_pages():
    body='<div class="markdown-body"><p>更新说明<br>修复问题</p></div>'
    assets='<ul><li><a href="/reunionSama/AuroraLauncher/releases/download/publicLauncher/AuroraLauncher.exe">AuroraLauncher.exe</a><span>sha256:'+'a'*64+'</span><relative-time datetime="2026-10-31T01:00:00Z"></relative-time></li></ul>'
    return body,assets

@pytest.mark.parametrize('status',[403,429])
def test_rate_limited_api_falls_back_to_fixed_release_page(tmp_path,status):
    checker=UpdateChecker(tmp_path);body,assets=web_pages();calls=[]
    def get(url,headers=None):
        calls.append(url)
        if url==API_URL:return status,{},''
        return 200,{},body if url==RELEASE_URL else assets
    checker._get=get;result=checker.check(True)
    assert result['candidate']['digest']=='a'*64 and '备用' in result['source']
    assert result['candidate']['body']=='更新说明\n修复问题'
    assert set(calls)=={API_URL,RELEASE_URL,ASSETS_URL}
    calls.clear();assert checker.check(True)['candidate'];assert calls==[]
    saved=json.loads(checker.file.read_text());saved['checked_at']=time.time()-100;atomic_json(checker.file,saved)
    checker.check(True);assert API_URL not in calls # API limit is remembered across app restarts.

def test_etag_304_reuses_valid_release(tmp_path):
    checker=UpdateChecker(tmp_path);atomic_json(checker.file,{'release':release(),'checked_at':time.time()-2000,'etag':'"abc"'})
    checker._get=Mock(return_value=(304,{},''));assert checker.check(True)['candidate']
    assert checker._get.call_args.args[1]=={'If-None-Match':'"abc"'}

def test_offline_cache_is_explicitly_marked_stale(tmp_path):
    checker=UpdateChecker(tmp_path);atomic_json(checker.file,{'release':release(),'checked_at':time.time()-2000})
    checker._get=Mock(side_effect=requests.Timeout());result=checker.check(True)
    assert result['stale'] and '不能确认' in result['source'] and '未能联网' in result['message']

def test_total_update_failure_has_useful_message_without_raw_http_error(tmp_path):
    checker=UpdateChecker(tmp_path);checker._get=Mock(side_effect=requests.Timeout())
    with pytest.raises(RuntimeError,match='备用通道'):checker.check(True)

def test_old_public_launcher_cannot_downgrade_desktop():assert newer_asset(release('2026-10-28T14:02:20Z')) is None

def test_reuploading_old_version_does_not_offer_a_downgrade():
    value=release();value['body']='公测 V1.0.0';assert newer_asset(value) is None

def test_changed_file_in_same_tag_is_detected():assert newer_asset(release())['version']=='20261031-010000'

def test_unsigned_update_cannot_be_downloaded():
    value=release();value['assets'][0]['digest']=''
    with pytest.raises(ValueError,match='SHA-256'):newer_asset(value)

def test_webpage_parser_rejects_missing_assets():
    with pytest.raises(ValueError):parse_web('<h1>Error</h1>','')
