"""Build our Java 8 compatible agent with a pinned and privately relocated ASM."""
from pathlib import Path
import hashlib,os,shutil,struct,subprocess,sys,zipfile,urllib.request

ROOT=Path(__file__).resolve().parent
ASM_VERSION='9.9'
ASM_SHA256='03d99a74ad1ee5c71334ef67437f4ef4fe3488caa7c96d8645abc73c8e2017d4'

def relocate(data):
    # Only change CONSTANT_Utf8 entries, preserving every other classfile byte.
    count=struct.unpack_from('>H',data,8)[0];out=bytearray(data[:10]);pos=10;index=1
    lengths={3:4,4:4,5:8,6:8,7:2,8:2,9:4,10:4,11:4,12:4,15:3,16:2,17:4,18:4,19:2,20:2}
    while index<count:
        tag=data[pos];out.append(tag);pos+=1
        if tag==1:
            length=struct.unpack_from('>H',data,pos)[0];pos+=2
            value=data[pos:pos+length].replace(b'org/objectweb/asm',b'io/github/reunionsama/aurora/shaded/asm').replace(b'org.objectweb.asm',b'io.github.reunionsama.aurora.shaded.asm');pos+=length;out.extend(struct.pack('>H',len(value)));out.extend(value)
        else:
            length=lengths[tag];out.extend(data[pos:pos+length]);pos+=length
            if tag in (5,6):index+=1
        index+=1
    out.extend(data[pos:]);return bytes(out)

def main():
    folder=ROOT/'build/branding';folder.mkdir(parents=True,exist_ok=True);jar=folder/'asm.jar'
    if not jar.exists() or hashlib.sha256(jar.read_bytes()).hexdigest()!=ASM_SHA256:
        urls=['https://maven.aliyun.com/repository/central/org/ow2/asm/asm/'+ASM_VERSION+'/asm-'+ASM_VERSION+'.jar','https://repo.maven.apache.org/maven2/org/ow2/asm/asm/'+ASM_VERSION+'/asm-'+ASM_VERSION+'.jar']
        for url in urls:
            try:
                data=urllib.request.urlopen(url,timeout=45).read();assert hashlib.sha256(data).hexdigest()==ASM_SHA256;jar.write_bytes(data);break
            except Exception:
                if url==urls[-1]:raise
    classes=folder/'classes';classes.mkdir(exist_ok=True);sources=[str(p) for p in (ROOT/'java').rglob('*.java')]
    javac=shutil.which('javac')
    if javac:command=[javac,'--release','8','-encoding','UTF-8','-cp',str(jar),'-d',str(classes),*sources]
    elif os.environ.get('AURORA_ECJ'):command=['java','-jar',os.environ['AURORA_ECJ'],'-8','-encoding','UTF-8','-cp',str(jar),'-d',str(classes),*sources]
    else:raise RuntimeError('Building the branding component requires a JDK (javac)')
    subprocess.run(command,check=True)
    target=ROOT/'assets/AuroraBranding.jar';target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as output:
        output.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\r\nPremain-Class: io.github.reunionsama.aurora.AuroraBranding\r\n\r\n')
        for p in classes.rglob('*.class'):output.writestr(p.relative_to(classes).as_posix(),relocate(p.read_bytes()))
        with zipfile.ZipFile(jar) as source:
            for entry in source.namelist():
                if entry.startswith('org/objectweb/asm/') and entry.endswith('.class'):output.writestr(entry.replace('org/objectweb/asm','io/github/reunionsama/aurora/shaded/asm'),relocate(source.read(entry)))
        output.writestr('META-INF/ASM-LICENSE.txt',(ROOT/'assets/THIRD_PARTY_NOTICES.txt').read_text('utf-8').split('ASM 9.9, redistributed with package names relocated to avoid game conflicts:')[1])
    print('Built AuroraBranding.jar (private ASM namespace, Java 8 bytecode)')
if __name__=='__main__':main()
