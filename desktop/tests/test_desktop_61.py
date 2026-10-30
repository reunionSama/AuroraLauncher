import json,math,os,re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from PySide6.QtCore import QByteArray,QBuffer,QIODevice
from PySide6.QtGui import QImage,QColor,QPainter
from PySide6.QtWidgets import QApplication
from aurora.auth import profile_skin
from aurora.skins import SkinCache
from aurora.installers import InstallerCatalog,validate_plan
from aurora.storage import Store
from aurora.i18n import translate,catalog,LANGUAGES

ASSETS=Path(__file__).resolve().parents[1]/'assets'
SKIN='https://textures.minecraft.net/texture/'+'a'*64
CAPE='https://textures.minecraft.net/texture/'+'c'*64

@pytest.fixture(scope='module')
def app():
    instance=QApplication.instance() or QApplication([])
    yield instance

def test_profile_uses_only_active_cape_and_clears_removed_cape():
    meta=profile_skin({'skins':[],'capes':[{'id':'old','state':'INACTIVE','url':SKIN},{'id':'active','state':'ACTIVE','url':CAPE}]})
    assert meta['cape']==CAPE and meta['cape_id']=='active'
    assert profile_skin({'skins':[],'capes':[]})['cape']==''

def png(width,height,color):
    image=QImage(width,height,QImage.Format.Format_ARGB32);image.fill(QColor(color));data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'PNG');return bytes(data)

class Response:
    status_code=200;headers={}
    def __init__(self,data):self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):pass
    def iter_content(self,n):yield self.data

def test_skin_and_cape_download_and_reuse_same_account_cache(tmp_path):
    session=Mock();session.headers={};session.get.side_effect=[Response(png(64,64,'blue')),Response(png(64,32,'red'))]
    cache=SkinCache(tmp_path,session=session);result=cache.resolve({'skin':SKIN,'cape':CAPE},False)
    assert Path(result['path']).is_file() and Path(result['cape_path']).is_file()
    assert session.get.call_count==2
    session.get.reset_mock();again=cache.resolve({'skin':SKIN,'cape':CAPE},False)
    assert again['cape_path']==result['cape_path'] and session.get.call_count==0

def test_cape_is_visible_from_behind_and_can_be_removed(app,tmp_path):
    from aurora.visuals import PlayerView
    skin=tmp_path/'skin.png';skin.write_bytes(png(64,64,'blue'));cape=tmp_path/'cape.png';cape.write_bytes(png(64,32,'red'))
    view=PlayerView();view.setWidth(280);view.setHeight(400);view.setSkin(str(skin));view._yaw=math.pi
    def red_pixels():
        image=QImage(280,400,QImage.Format.Format_ARGB32);image.fill(0);p=QPainter(image);view.paint(p);p.end()
        return sum(image.pixelColor(x,y).red()>200 and image.pixelColor(x,y).blue()<50 for y in range(400) for x in range(280))
    assert red_pixels()==0;view.setCape(str(cape));assert red_pixels()>1000;view.setCape('');assert red_pixels()==0;view.timer.stop()

@pytest.mark.parametrize('loader',['fabric','forge','neoforge','quilt','optifine'])
def test_exact_loader_version_is_required(loader):
    with pytest.raises(ValueError,match='具体版本'):validate_plan({'minecraft':'1.20.1','loader':loader})
    assert validate_plan({'minecraft':'1.20.1','loader':loader,'loader_version':'1.2.3'})==( '1.20.1',loader,'1.2.3')

@pytest.mark.parametrize('kind,loader',[('fabric-api','forge'),('quilt-api','fabric')])
def test_incompatible_api_is_rejected(kind,loader):
    with pytest.raises(ValueError,match='需要'):validate_plan({'minecraft':'1.20.1','loader':loader,'loader_version':'1',kind:'api-version'})

@pytest.mark.parametrize('kind',['fabric','quilt'])
def test_loader_catalog_uses_selected_game_version(kind):
    net=Mock();net.json.return_value=[{'loader':{'version':'0.18.0','stable':True}}]
    value=InstallerCatalog(SimpleNamespace(net=net)).choices(kind,'1.21.11')
    assert value[0]['id']=='0.18.0' and '/versions/loader/1.21.11' in net.json.call_args.args[0]

@pytest.mark.parametrize('game,expected',[('1.21.1','21.1.'),('1.20.4','20.4.'),('26.3','26.3.')])
def test_neoforge_filters_both_legacy_and_year_based_versions(game,expected):
    net=Mock();net.json.return_value={'versions':['21.1.1','20.4.237','26.3.0.5','26.1.0.2']}
    values=InstallerCatalog(SimpleNamespace(net=net)).choices('neoforge',game)
    assert values and all(v['id'].startswith(expected) for v in values)

def test_forge_catalog_never_mix_game_versions():
    net=Mock();obj=InstallerCatalog(SimpleNamespace(net=net));obj._text=Mock(return_value='<metadata><versioning><versions><version>1.20.1-47.2.18</version><version>1.21.1-52.0.1</version></versions></versioning></metadata>')
    assert obj.choices('forge','1.20.1')==[{'id':'47.2.18','label':'47.2.18','stable':True}]

def test_late_component_response_cannot_replace_new_game_choices(app,tmp_path):
    from aurora.bridge import Bridge
    bridge=Bridge(Store(tmp_path),ASSETS,True);bridge.submit=Mock()
    try:
        bridge.prepareInstaller('1.20.1');old=bridge._catalog_generation;bridge.prepareInstaller('1.21.1')
        bridge._catalog_result('component-'+str(old)+'-fabric',[{'id':'old','label':'old'}],'')
        assert bridge.installer['minecraft']=='1.21.1' and all(not row['choices'] for row in bridge.installer['rows'])
    finally:bridge.close()

@pytest.mark.parametrize('language',['en_US','ja_JP','ko_KR'])
def test_all_interface_strings_have_complete_translations(language):
    text=(ASSETS.parent/'qml/Main.qml').read_text();strings=re.findall(r'root\.t\(("(?:[^"\\]|\\.)*")\)',text)
    for raw in strings:
        key=json.loads(raw)
        assert key in catalog(),key
        assert catalog()[key].get(language),key
        assert translate(key,language)==catalog()[key][language]

def test_language_is_immediate_and_persisted(app,tmp_path):
    from aurora.bridge import Bridge
    bridge=Bridge(Store(tmp_path),ASSETS,True)
    try:
        bridge.setSetting('language','ja_JP');assert bridge.translate('启动游戏')=='ゲームを起動'
        bridge.store.save();assert Store(tmp_path).settings['language']=='ja_JP'
        bridge.setSetting('language','bad');assert bridge.settings['language']=='ja_JP'
    finally:bridge.close()

def test_home_instruction_removed_without_removing_drag_or_twenty_actions():
    text=(ASSETS.parent/'qml/Main.qml').read_text()
    assert '左右拖动旋转 · 点击人物互动 · 20 种动作' not in text
    assert 'player.yawAngle+=' in text and 'player.triggerAction()' in text
    from aurora.visuals import NAMES
    assert len(NAMES)==20
