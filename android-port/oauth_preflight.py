"""Registration check only. Never print, store or poll the device/user codes."""
import json
from pathlib import Path
import sys
import urllib.request
import urllib.parse
import urllib.error

CLIENT_ID='785d7402-026c-44d0-ae65-d4b29eb27d3c'
result={'client_id':CLIENT_ID,'test':'device-code registration only; no user sign-in'}
try:
    request=urllib.request.Request('https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode',data=urllib.parse.urlencode({'client_id':CLIENT_ID,'scope':'XboxLive.signin offline_access openid profile email'}).encode())
    try:
        response=urllib.request.urlopen(request,timeout=25)
    except urllib.error.HTTPError as exc:
        response=exc
    data=json.loads(response.read())
    result.update(http_status=response.status,device_code_issued=bool(data.get('device_code')))
    if response.status!=200:
        result.update(error=data.get('error'),description=data.get('error_description'),error_codes=data.get('error_codes'))
except Exception as exc:
    result['network_error']=type(exc).__name__+': '+str(exc)
Path(sys.argv[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))



