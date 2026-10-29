"""Launch/UI smoke only; no accounts, credentials or gameplay involved."""
import json,re,subprocess,time,sys,xml.etree.ElementTree as ET
from pathlib import Path
out=Path('smoke-results');out.mkdir(exist_ok=True)
pkg='io.github.reunionsama.auroralauncher.android'
report={'physical_device':False,'gameplay_tested':False,'login_tested':False,'tool_screen_reached':False}
def adb(*args,check=False):
    r=subprocess.run(['adb',*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    if check and r.returncode: raise RuntimeError(r.stdout[-2000:])
    return r.stdout

def snapshot():
    adb('shell','uiautomator','dump','/sdcard/aurora-smoke.xml')
    text=adb('shell','cat','/sdcard/aurora-smoke.xml')
    try:return ET.fromstring(text[text.index('<?xml'):])
    except (ValueError,ET.ParseError):return None

def tap(node):
    nums=list(map(int,re.findall(r'[0-9]+',node.get('bounds',''))))
    if len(nums)==4:adb('shell','input','tap',str((nums[0]+nums[2])//2),str((nums[1]+nums[3])//2))

try:
    report['emulator_abis']=adb('shell','getprop','ro.product.cpu.abilist').strip()
    report['native_bridge']=adb('shell','getprop','ro.dalvik.vm.native.bridge').strip()
    result=adb('install','--abi','arm64-v8a',sys.argv[1])
    report['install_output']=result.strip()
    if 'Success' not in result:raise RuntimeError('Emulator cannot install the ARM64 build: '+result)
    adb('logcat','-c')
    report['launch_output']=adb('shell','am','start','-W','-n',pkg+'/com.movtery.zalithlauncher.ui.activities.SplashActivity')
    deadline=time.monotonic()+100
    while time.monotonic()<deadline:
        tree=snapshot()
        if tree is not None:
            nodes=list(tree.iter('node'))
            tool=next((n for n in nodes if 'Aurora 工具' in (n.get('text','')+n.get('content-desc',''))),None)
            if tool is not None:
                # First-run guide popups do not always appear in UIAutomator's window tree.
                # Click a harmless empty margin to complete all guide steps before interacting.
                for _ in range(8):
                    adb('shell','input','tap','20','200');time.sleep(.8)
                tree=snapshot();nodes=list(tree.iter('node')) if tree is not None else []
                tool=next((n for n in nodes if 'Aurora 工具' in (n.get('text','')+n.get('content-desc',''))),tool)
                with (out/'home.png').open('wb') as f:subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
                custom=next((n for n in nodes if n.get('text')=='极光与个性化'),None)
                report['aurora_home_visible']=custom is not None
                if custom is not None:
                    tap(custom);time.sleep(1)
                    tree=snapshot()
                    report['personalization_opened']=tree is not None and any('让 Aurora 更像你的启动器' in n.get('text','') for n in tree.iter('node'))
                    if report.get('personalization_opened'):
                        with (out/'personalization.png').open('wb') as f:subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
                        adb('shell','input','keyevent','4');time.sleep(1)
                    tree=snapshot();nodes=list(tree.iter('node')) if tree is not None else []
                    tool=next((n for n in nodes if 'Aurora 工具' in (n.get('text','')+n.get('content-desc',''))),tool)
                tap(tool);time.sleep(2)
                tree=snapshot()
                if tree is not None and any('我的工作台' in n.get('text','') for n in tree.iter('node')):
                    report['tool_screen_reached']=True
                    (out/'tools-ui.xml').write_text(ET.tostring(tree,encoding='unicode'))
                    with (out/'tools.png').open('wb') as f:subprocess.run(['adb','exec-out','screencap','-p'],stdout=f,check=True)
                    # Exercise each Aurora tab and verify visible content.
                    for label,expected in [('启动前检查','快速检查'),('网络诊断','请求卡在哪里'),('日志速览','这次启动发生了什么')]:
                        tree=snapshot();node=next((n for n in tree.iter('node') if n.get('text')==label),None)
                        if node is not None:
                            tap(node);time.sleep(1);after=snapshot()
                            report[label]=after is not None and any(expected in n.get('text','') for n in after.iter('node'))
                    break
            # Only consent to the displayed local GPL component setup, or dismiss first-run guides.
            for n in nodes:
                text=n.get('text','').strip().lower()
                if text in {'agree and continue','同意并继续','我已阅读并同意','同意','agree','i agree','skip','跳过','稍后','later','我知道了','got it','install','安装','next','下一步','cancel','取消'}:
                    tap(n);break
        if not adb('shell','pidof',pkg).strip():raise RuntimeError('Launcher process exited; see logcat.')
        time.sleep(2)
    if not report['tool_screen_reached']:raise RuntimeError('Did not reach Aurora workspace within the first-run timeout.')
except Exception as e:
    report['error']=str(e)[:2500]
finally:
    (out/'logcat.txt').write_text(adb('logcat','-d','-t','1500'))
    tree=snapshot()
    if tree is not None:(out/'last-ui.xml').write_text(ET.tostring(tree,encoding='unicode'))
    (out/'smoke-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
if not report['tool_screen_reached'] or any(report.get(k) is not True for k in ['启动前检查','网络诊断','日志速览']):sys.exit(1)


