"""Pin the same loader identification icons as the Android upstream (GPL notices retained)."""
from pathlib import Path
import hashlib,json,io,time,urllib.request
from PIL import Image

def prepare_icons():
    root=Path(__file__).parent/'assets';manifest=json.loads((root/'loader-sources.json').read_text())
    dest=root/'loaders';dest.mkdir(exist_ok=True)
    for entry in manifest['icons']:
        out=dest/(entry['name']+'.png')
        url='https://raw.githubusercontent.com/'+manifest['repository']+'/'+manifest['commit']+'/'+entry['path']
        error=None
        for attempt in range(3):
            try:
                data=urllib.request.urlopen(url,timeout=30).read()
                actual=hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()
                if actual!=entry['blob']:raise ValueError('Loader icon did not match pinned Git blob')
                image=Image.open(io.BytesIO(data)).convert('RGBA');image.thumbnail((128,128));image.save(out);break
            except Exception as exc:error=exc;time.sleep(.3)
        else:raise RuntimeError('Could not prepare '+entry['name']) from error
    for kind,base in [('fabric-api','fabric'),('quilt-api','quilt')]:
        (dest/(kind+'.png')).write_bytes((dest/(base+'.png')).read_bytes())

if __name__=='__main__':prepare_icons()
