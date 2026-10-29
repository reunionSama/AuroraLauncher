"""Code-native Aurora icon assets; deterministic PNG export without external tools."""
from pathlib import Path
import hashlib
import json
import struct
import zlib


def png(size, avatar=False, rounded=False):
    rows = bytearray()
    for iy in range(size):
        rows.append(0)
        for ix in range(size):
            x, y = (ix+.5)/size, (iy+.5)/size
            dx, dy = abs(x-.5), abs(y-.5)
            color = (16,28,37,255)
            if avatar:
                if ((x-.5)**2+(y-.34)**2 < .14**2 or
                    (y>.56 and ((x-.5)/.30)**2+((y-.84)/.28)**2 < 1)):
                    color = (151,218,226,255)
            else:
                if max(dx,dy)+2*min(dx,dy) <= 30/108:
                    color = (9,185,202,255)
                if dx+dy <= 11/108:
                    color = (228,250,255,255)
            if rounded and dx*dx+dy*dy>.49**2:
                color=(0,0,0,0)
            rows.extend(color)
    def chunk(name, data):
        return struct.pack('!I',len(data))+name+data+struct.pack('!I',zlib.crc32(name+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(rows),9))+chunk(b'IEND',b'')


def replace_branding(module):
    module=Path(module)
    res=module/'src/main/res'
    stems={'img_launcher','ic_launcher','ic_launcher_round','img_avatar_movtery','img_sponsor'}
    originals={str(p.relative_to(module)):hashlib.sha256(p.read_bytes()).hexdigest()
               for p in res.rglob('*') if p.is_file() and p.stem in stems and p.suffix in {'.png','.webp'}}
    outputs=[]
    for old in list(res.rglob('*')):
        if not old.is_file() or old.stem not in stems or old.suffix not in {'.png','.webp'}:
            continue
        stem=old.stem; parent=old.parent
        density={'mipmap-mdpi':48,'mipmap-hdpi':72,'mipmap-xhdpi':96,'mipmap-xxhdpi':144,'mipmap-xxxhdpi':192}
        size=density.get(parent.name,192)
        old.unlink()
        new=parent/(stem+'.png')
        new.write_bytes(png(size,avatar=stem in {'img_avatar_movtery','img_sponsor'},rounded=stem=='ic_launcher_round'))
        outputs.append(str(new.relative_to(module)))
    # Some future resource configurations may not contain the base drawable.
    logo=res/'drawable/img_launcher.png';logo.parent.mkdir(parents=True,exist_ok=True)
    logo.write_bytes(png(192))
    play=module/'src/main/ic_launcher-playstore.png';play.write_bytes(png(512))
    forbidden=set(originals.values())
    leftovers=[str(p.relative_to(module)) for p in res.rglob('*') if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() in forbidden]
    if leftovers:
        raise RuntimeError('Upstream branded image remained: '+str(leftovers))
    audit={'replaced_raster_resources':sorted(outputs),'original_resource_digests':originals,'leftover_original_images':leftovers}
    (module.parent/'AURORA_BRANDING_AUDIT.json').write_text(json.dumps(audit,indent=2))
    return audit



