"""Capture the real setup welcome page, then install and run the installed EXE."""
import ctypes,json,os,subprocess,sys,time
from ctypes import wintypes
from pathlib import Path
from PIL import ImageGrab

def capture(setup,out):
    user=ctypes.windll.user32;process=subprocess.Popen([str(setup),'/SP-','/LANG=english'])
    found=[];CB=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    @CB
    def enum(hwnd,param):
        pid=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        text=ctypes.create_unicode_buffer(300);user.GetWindowTextW(hwnd,text,300)
        if user.IsWindowVisible(hwnd) and 'AuroraLauncher' in text.value and ('Setup' in text.value):found.append(hwnd)
        return True
    try:
        deadline=time.monotonic()+25
        while not found and time.monotonic()<deadline:user.EnumWindows(enum,0);time.sleep(.2)
        if not found:raise RuntimeError('Setup wizard window was not visible')
        hwnd=found[-1];user.SetForegroundWindow(hwnd);time.sleep(.8);rect=wintypes.RECT();user.GetWindowRect(hwnd,ctypes.byref(rect))
        ImageGrab.grab(bbox=(rect.left,rect.top,rect.right,rect.bottom),all_screens=True).save(out)
    finally:
        # Only terminate the still-idle welcome UI; no installation has begun.
        # Inno Setup's initial stub can spawn the actual UI, so stop the tree.
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)

def main():
    setup=Path(sys.argv[1]).resolve();evidence=Path(sys.argv[2]).resolve();evidence.mkdir(parents=True,exist_ok=True)
    capture(setup,evidence/'installer-welcome.png')
    target=Path(os.environ['RUNNER_TEMP'])/'Aurora-installed-test'
    subprocess.run([str(setup),'/SP-','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR='+str(target),'/LOG='+str(evidence/'setup.log')],check=True,timeout=180)
    exe=target/'AuroraLauncher.exe'
    if not exe.is_file():raise RuntimeError('Installed EXE is missing')
    subprocess.run([str(exe),'--self-test','--data-dir',str(target/'test-data'),'--test-report',str(evidence/'installed-ui.json'),'--screenshot-dir',str(evidence/'installed-screens')],check=True,timeout=70)
    report=json.loads((evidence/'installed-ui.json').read_text('utf-8'))
    if not report['ok'] or not report['frozen']:raise RuntimeError('Installed application failed UI tests')
    (evidence/'installer.json').write_text(json.dumps({'ok':True,'installed_exe':str(exe),'setup_size_bytes':setup.stat().st_size,'welcome_captured':True,'installed_ui':report['ok']},indent=2),'utf-8')
    # Remove program files only; never test against real user data.
    subprocess.run([str(target/'unins000.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=60)

if __name__=='__main__':main()
