"""Verify the official Windows Terracotta process and local API; no rooms or peers."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aurora.storage import Store
from aurora.engine import Engine
from aurora.terracotta import Terracotta
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
e=Engine(Store(root));t=Terracotta(e);report={'ok':False,'room_created':False,'peer_connection_tested':False}
try:
    t.ensure();meta=t.call('/meta').json();state=t.state();report.update(ok=str(meta.get('version','')).lstrip('v')=='0.4.2',version=meta.get('version'),state=state.get('state'),local_http_api=True)
finally:
    if t.port:
        try:t.call('/panic',{'peaceful':'true'})
        except Exception:pass
    out.write_text(json.dumps(report,indent=2))
if not report['ok']:raise RuntimeError('Terracotta component did not start')
print('Official Terracotta Windows process and loopback API verified.')
