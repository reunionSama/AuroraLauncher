"""Test registration with the real client ID without user sign-in or token polling."""
import json,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aurora import CLIENT_ID
from aurora.auth import Auth,verification_url

result={'client_id':CLIENT_ID,'test':'device registration only','user_sign_in_tested':False}
try:
    device=Auth(threading.Event()).start()
    url=verification_url(device)
    result.update(ok=bool(device.get('device_code') and device.get('user_code')),verification_uri=url)
except Exception as exc:result.update(ok=False,error=str(exc))
Path(sys.argv[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps(result,ensure_ascii=False))
sys.exit(0 if result['ok'] else 1)
