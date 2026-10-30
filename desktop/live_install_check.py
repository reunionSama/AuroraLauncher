import os,sys,time,json,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from aurora.storage import Store
from aurora.engine import Engine
from aurora.auth import Auth
root=Path(sys.argv[1]);s=Store(root);s.settings['workers']=16;s.settings['source']='official';s.save()
def progress(text,n,total):
 if n==0 or n==total or n%200==0:print(text,n,total,flush=True)
e=Engine(s,progress,print)
start=time.time();v=e.install('1.20.1');cmd=e.make_command(v,{'name':'AuroraTester','uuid':'00000000000030008000000000000001','access_token':'0'},s.game_dir(),demo=True)
assert '-Xmx4096M' in cmd and '--demo' in cmd
assert any('1.20.1.jar' in a for a in cmd)
for x in cmd:
 if x.endswith('.jar') and os.pathsep not in x:assert Path(x).is_file(),x
r={'install_ok':True,'seconds':round(time.time()-start,2),'java':cmd[0],'command_built':True,'version':v}
try:d=Auth(threading.Event()).start();r['microsoft_device_registration']=bool(d.get('device_code'))
except Exception as ex:r['microsoft_device_registration']=False;r['microsoft_error']=str(ex)
(root/'install-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
