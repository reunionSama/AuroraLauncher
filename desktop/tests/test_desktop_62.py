import json,math,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest,requests
from PySide6.QtCore import Qt,QEventLoop,QTimer
from PySide6.QtGui import QImage,QColor,QPainter
from PySide6.QtWidgets import QApplication
from aurora.storage import Store,atomic_json
from aurora.installers import validate_plan
from aurora.network import Net
from aurora.modrinth_net import ModrinthAPI,OFFICIAL,validate_endpoint

@pytest.fixture(scope='module')
def app():return QApplication.instance() or QApplication([])

def test_no_animation_wakeups_when_suspended(app):
    from aurora.visuals import AuroraView,PlayerView
    for cls in (AuroraView,PlayerView):
        view=cls();view.setActive(False);before=view._frames
        assert not view.timer.isActive()
        view.tick();assert view._frames==before
        view.setFps(60);assert not view.timer.isActive()
        view.setActive(True);assert view.timer.isActive()
        view.setActive(False)

def test_player_remains_rotatable_with_reduced_motion(app):
    from aurora.visuals import PlayerView
    view=PlayerView();view.setActive(False);view.setYaw(1.4)
    assert view._yaw==1.4

def test_cape_outer_artwork_faces_away_from_player(app,tmp_path):
    from aurora.visuals import PlayerView
    skin=QImage(64,64,QImage.Format.Format_ARGB32);skin.fill(QColor('#333333'));skin.save(str(tmp_path/'skin.png'))
    cape=QImage(64,32,QImage.Format.Format_ARGB32);cape.fill(0)
    paint=QPainter(cape);paint.fillRect(1,1,10,16,QColor('red'));paint.fillRect(12,1,10,16,QColor('blue'));paint.end();cape.save(str(tmp_path/'cape.png'))
    view=PlayerView();view.setActive(False);view.setWidth(280);view.setHeight(400);view.setSkin(str(tmp_path/'skin.png'));view.setCape(str(tmp_path/'cape.png'));view.setYaw(math.pi)
    image=QImage(280,400,QImage.Format.Format_ARGB32);image.fill(0);p=QPainter(image);view.paint(p);p.end()
    red=blue=0
    for y in range(400):
        for x in range(280):
            c=image.pixelColor(x,y)
            red+=c.red()>200 and c.blue()<50
            blue+=c.blue()>200 and c.red()<50
    assert red>1000 and red>4*blue

@pytest.mark.parametrize('plan',[
    {'loader':'fabric','fabric':'a','forge':'b'},
    {'loader':'forge','fabric':'a'},
    {'loader':['fabric','forge']},
    {'loader':'fabric','quilt-api':'api'}])
def test_mixed_loaders_rejected_before_install(plan):
    with pytest.raises(ValueError):validate_plan({'minecraft':'1.20.1','loader_version':'1',**plan})

def test_log_and_network_timers_are_idle_until_needed(app,tmp_path):
    from aurora.bridge import Bridge
    b=Bridge(Store(tmp_path),Path(__file__).resolve().parents[1]/'assets',True)
    try:
        b.logtimer.stop();b._flush_logs()
        assert not b.logtimer.isActive() and not b.terratimer.isActive()
        b._append_log('a'*12000);assert b.logtimer.isActive() and len(b._log[-1])<8300
        b._flush_logs();b.logtimer.stop();b._poll_terra();assert not b.terratimer.isActive()
        b.finishSetup();assert Store(tmp_path).settings['setupCompleted']
    finally:b.close()

class Response:
    def __init__(self,data=b'{}',status=200,headers=None):self.data=data;self.status_code=status;self.headers=headers or {}
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def iter_content(self,n):yield self.data
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError('HTTP '+str(self.status_code),response=self)

def api(tmp_path):
    net=Net(tmp_path/'cache');session=Mock();net.session=Mock(return_value=session)
    engine=SimpleNamespace(net=net,store=Store(tmp_path/'data'))
    return ModrinthAPI(engine),session,engine

def test_modrinth_recovers_transient_failure_and_caches(tmp_path):
    client,session,engine=api(tmp_path)
    session.get.side_effect=[requests.Timeout(),Response(b'{"hits":[]}')]
    url=OFFICIAL+'/search?query=sodium'
    assert client.json(url)=={'hits':[]} and session.get.call_count==2
    session.get.reset_mock();assert client.json(url)=={'hits':[]} and not session.get.called

def test_modrinth_rate_limit_respects_cooldown_and_marks_stale_cache(tmp_path):
    client,session,engine=api(tmp_path);url=OFFICIAL+'/search?query=sodium'
    import hashlib
    p=engine.net.cache/('modrinth-'+hashlib.sha256(url.encode()).hexdigest()+'.json')
    atomic_json(p,{'at':time.time()-3600,'body':{'hits':[{'title':'cached'}]}})
    session.get.return_value=Response(status=429,headers={'Retry-After':'60'})
    assert client.json(url,stale=True)['hits'][0]['title']=='cached'
    assert session.get.call_count==1 and '缓存' in client.notice
    with pytest.raises(RuntimeError):client.json(url,stale=False)
    assert session.get.call_count==1

def test_opt_in_mirror_then_official_keeps_query_and_no_auth(tmp_path):
    client,session,engine=api(tmp_path);client.alternate='https://mirror.example/v2'
    session.get.side_effect=[Response(status=404),Response(b'[]')]
    assert client.json(OFFICIAL+'/project/fabric-api/version?x=1')==[]
    assert session.get.call_args_list[0].args[0]=='https://mirror.example/v2/project/fabric-api/version?x=1'
    assert session.get.call_args_list[1].args[0].startswith(OFFICIAL)
    assert all('Authorization' not in call.kwargs['headers'] for call in session.get.call_args_list)

@pytest.mark.parametrize('url',['http://mirror.example/v2','https://u:pw@mirror.example/v2','https://mirror.example/v2?token=a','https://mirror.example/v3'])
def test_endpoint_must_be_valid_https_api(url):
    with pytest.raises(ValueError):validate_endpoint(url)

def test_project_icons_are_downloaded_once_and_bounded(app,tmp_path):
    from aurora.images import IconCache
    from PySide6.QtCore import QByteArray,QBuffer,QIODevice
    image=QImage(256,256,QImage.Format.Format_ARGB32);image.fill(QColor('red'))
    data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'PNG')
    client,session,engine=api(tmp_path);session.get.return_value=Response(bytes(data))
    cache=IconCache(engine.net);url='https://cdn.modrinth.com/data/test/icon.png'
    assert cache.fetch(url).startswith('file:')
    assert max(QImage(str(cache.path(url))).size().toTuple())<=96
    assert cache.fetch(url)==cache.cached(url) and session.get.call_count==1
    assert cache.fetch('https://untrusted.example/huge.png')==''

def test_update_prefers_installer_and_rejects_old_file():
    from aurora.updates import newer_asset
    from aurora import PROJECT
    def item(name):return {'name':name,'browser_download_url':PROJECT+'/releases/download/publicLauncher/'+name,'digest':'sha256:'+'a'*64,'updated_at':'2026-11-03T00:00:00Z'}
    value=newer_asset({'name':'v6.3.0','assets':[item('AuroraLauncher.exe'),item('AuroraLauncher-Setup.exe')]})
    assert value['filename']=='AuroraLauncher-Setup.exe'


def test_search_bursts_keep_only_the_latest_pending_request(app,tmp_path):
    from aurora.bridge import Bridge
    b=Bridge(Store(tmp_path),Path(__file__).resolve().parents[1]/'assets',True)
    try:
        for i in range(25):b.searchMods(str(i),'mod')
        assert b._pending_search==(25,'24','mod')
        assert not any(k.startswith('search-') for k in b._jobs)
        b._jobs['search-1']=False;b._dispatch_search()
        assert b._pending_search==(25,'24','mod')
    finally:b.close()
