# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
import hashlib,json,threading,zipfile,time
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
import pytest
from aurora.storage import Store,Vault,safe_path,atomic_json,redact
from aurora.auth import offline
from aurora.network import Net,Cancelled
from aurora.engine import Engine
from aurora.visuals import gesture

@pytest.fixture
def http_server():
    data=(b'Aurora download integrity test\n'*1024)
    state={'ranges':[],'calls':0}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state['calls']+=1
            if self.path=='/metadata':
                payload=json.dumps({'ok':True}).encode();self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
            if self.path=='/bad':payload=b'corrupt';offset=0
            else:
                offset=int(self.headers.get('Range','bytes=0-').split('=')[1].split('-')[0]);state['ranges'].append(offset);payload=data[offset:]
            self.send_response(206 if offset else 200)
            if offset:self.send_header('Content-Range',f'bytes {offset}-{len(data)-1}/{len(data)}')
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}',data,state
    server.shutdown();server.server_close()

def test_resume_download_is_verified_and_atomic(tmp_path,http_server):
    url,data,state=http_server;n=Net(tmp_path/'cache');target=tmp_path/'artifact.bin';target.with_name(target.name+'.part').write_bytes(data[:512])
    n.download(url+'/file',target,hashlib.sha256(data).hexdigest(),'sha256',len(data))
    assert target.read_bytes()==data and 512 in state['ranges']
    assert not target.with_name(target.name+'.part').exists()
    before=state['calls'];n.download(url+'/file',target,hashlib.sha256(data).hexdigest(),'sha256',len(data));assert state['calls']==before

def test_corruption_never_replaces_good_file(tmp_path,http_server):
    url,data,state=http_server;n=Net(tmp_path/'cache');target=tmp_path/'artifact.bin';target.write_bytes(b'old')
    with pytest.raises(RuntimeError,match='校验|大小'):n.download(url+'/bad',target,hashlib.sha256(data).hexdigest(),'sha256',len(data))
    assert target.read_bytes()==b'old'

def test_json_cache_allows_offline_read(tmp_path,http_server):
    url,data,state=http_server;n=Net(tmp_path/'cache');assert n.json(url+'/metadata',key='test',ttl=100)=={'ok':True}
    n.cancel.set()
    assert n.json(url+'/metadata',key='test',ttl=100)=={'ok':True}

def test_cancel_prevents_download(tmp_path,http_server):
    url,data,state=http_server;n=Net(tmp_path/'cache');n.cancel.set()
    with pytest.raises(Cancelled):n.download(url+'/file',tmp_path/'x')
    assert not (tmp_path/'x').exists()

@pytest.mark.parametrize('name',['../escape','/absolute','C:/escape','..\\escape','folder/../escape','folder/CON.txt','foo:bar','trailing.','folder/aux','folder/name '])
def test_windows_and_zip_path_traversal_rejected(tmp_path,name):
    with pytest.raises(ValueError):safe_path(tmp_path,name)

def test_atomic_json_survives_concurrent_writers(tmp_path):
    p=tmp_path/'same.json'
    with ThreadPoolExecutor(max_workers=8) as ex:list(ex.map(lambda i:atomic_json(p,{'number':i,'payload':'a'*10000}),range(40)))
    assert 0<=json.loads(p.read_text())['number']<40

def test_offline_uuid_is_java_compatible():
    a=offline('AuroraTester');assert a==offline('AuroraTester');assert a['uuid']!='0'*32;assert len(a['uuid'])==32
    assert a['uuid'][12]=='3' and a['uuid'][16] in '89ab'

def test_invalid_offline_name_is_not_launched():
    for name in ['a','name with spaces','a'*17,'../test']:
        with pytest.raises(ValueError):offline(name)

def test_secrets_are_encrypted_and_roundtrip(tmp_path):
    v=Vault(tmp_path);accounts=[dict(name='Tester',access_token='secret-access',refresh_token='secret-refresh')];v.write(accounts)
    assert b'secret-access' not in v.path.read_bytes() and b'secret-refresh' not in v.path.read_bytes();assert v.read()==accounts

def test_logs_do_not_expose_tokens():
    text=redact('Authorization: Bearer abcd.123 --accessToken privateKey refresh_token="refreshSecret" --uuid uuidSecret')
    for secret in ['abcd.123','privateKey','refreshSecret','uuidSecret']:assert secret not in text

def test_instance_isolation_and_persistence(tmp_path):
    s=Store(tmp_path);first=s.game_dir();s.create_instance('模组测试','1.20.1');second=s.game_dir();assert first!=second
    (first/'options.txt').write_text('first');assert not (second/'options.txt').exists();assert Store(tmp_path).instance()['name']=='模组测试'

def test_archive_extraction_rejects_unsafe_members(tmp_path):
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.txt','unsafe')
    with pytest.raises(ValueError):Engine.extract_zip(archive,tmp_path/'output')
    assert not (tmp_path/'escape.txt').exists()

def test_twenty_gestures_are_distinct_and_rest_at_endpoints():
    keys=set()
    for ident in range(20):
        pose,y=gesture(ident,.7);keys.add(tuple(round(x,5) for vec in pose.values() for x in vec)+(round(y,5),))
        for t in [0,3.2,3.5]:
            p,dy=gesture(ident,t);assert all(abs(x)<1e-8 for vec in p.values() for x in vec);assert abs(dy)<1e-8
    assert len(keys)==20

def test_gestures_do_not_snap_between_frames():
    for ident in range(20):
        for tick in range(320):
            a,ay=gesture(ident,tick/100);b,by=gesture(ident,(tick+1)/100)
            assert abs(ay-by)<.2
            assert max(abs(x-y) for key in a for x,y in zip(a[key],b[key]))<.2

def test_inherited_command_uses_base_jar_and_instance_directory(tmp_path):
    s=Store(tmp_path);e=Engine(s);base='1.20.1';child='fabric-test'
    root=s.library
    atomic_json(root/'versions'/base/(base+'.json'),{'id':base,'type':'release','mainClass':'net.minecraft.client.main.Main','libraries':[],'assets':'test','arguments':{'jvm':['-cp','${classpath}'],'game':['--username','${auth_player_name}','--gameDir','${game_directory}','--accessToken','${auth_access_token}']}})
    atomic_json(root/'versions'/child/(child+'.json'),{'id':child,'inheritsFrom':base,'jar':base,'type':'release','mainClass':'net.fabricmc.loader.impl.launch.knot.KnotClient','libraries':[]})
    e.java_for=lambda version:'java.exe'
    args=e.make_command(child,offline('AuroraTester'),s.game_dir());assert str(root/'versions'/base/(base+'.jar')) in args
    assert str(s.game_dir()) in args and 'net.fabricmc.loader.impl.launch.knot.KnotClient' in args

def test_neoforge_provider_exists():
    from minecraft_launcher_lib import mod_loader
    assert 'neoforge' in mod_loader.list_mod_loader()

def test_modern_client_id_xuid_and_quickplay_are_resolved(tmp_path):
    from aurora import CLIENT_ID
    s=Store(tmp_path);e=Engine(s);version='1.20.1';e.java_for=lambda v:'java'
    data={'id':version,'type':'release','mainClass':'net.minecraft.client.main.Main','libraries':[],'arguments':{'jvm':['-cp','${classpath}'],'game':['--clientId','${clientid}','--xuid','${auth_xuid}',{'rules':[{'action':'allow','features':{'is_quick_play_multiplayer':True}}],'value':['--quickPlayMultiplayer','${quickPlayMultiplayer}']}]}}
    atomic_json(s.library/'versions'/version/(version+'.json'),data)
    args=e.make_command(version,{**offline('AuroraTester'),'xuid':'123456'},s.game_dir(),server='127.0.0.1:25565')
    assert CLIENT_ID in args and '123456' in args
    assert '--quickPlayMultiplayer' in args and '127.0.0.1:25565' in args
    assert not any('${' in x for x in args)
