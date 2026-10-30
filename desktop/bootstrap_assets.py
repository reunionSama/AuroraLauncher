"""Fetch a pinned OFL font and generate reproducible original Aurora assets."""
from pathlib import Path
import hashlib,urllib.request
from make_assets import r
FONT_URL='https://raw.githubusercontent.com/notofonts/noto-cjk/f8d157532fbfaeda587e826d4cd5b21a49186f7c/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
EXPECTED='2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'
p=r/'NotoSansCJKsc-Regular.otf'
if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=EXPECTED:
    data=urllib.request.urlopen(FONT_URL,timeout=90).read()
    if hashlib.sha256(data).hexdigest()!=EXPECTED:raise RuntimeError('Font source changed; update its pinned hash deliberately')
    p.write_bytes(data)
print('Original Aurora assets and pinned OFL font ready.')
