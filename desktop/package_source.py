"""Package all build inputs/licenses, excluding caches, tests' user data and binaries."""
from pathlib import Path
import zipfile
root=Path(__file__).resolve().parents[1];out=root/'AuroraLauncher-Desktop-source.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for folder in [root/'desktop',root/'.github']:
        for p in folder.rglob('*'):
            if not p.is_file() or any(x in p.parts for x in ('build','dist','__pycache__','.pytest_cache','.venv')):continue
            if p.suffix in ('.tmp','.pyc'):continue
            z.write(p,p.relative_to(root))
    for name in ['LICENSE','README.md']:
        if (root/name).exists():z.write(root/name,name)
print(out.name)
