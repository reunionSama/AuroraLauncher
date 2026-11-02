"""Compare shipped onefile 6.1.0 and installed 6.2.0 in the same Windows VM."""
import ctypes,json,os,statistics,subprocess,sys,time
from ctypes import wintypes
from pathlib import Path
import psutil
user=ctypes.windll.user32
user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
user.IsWindowVisible.argtypes=[wintypes.HWND]
user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
user.SetForegroundWindow.argtypes=[wintypes.HWND]
CALLBACK=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)

def family(pid):
    try:return [psutil.Process(pid),*psutil.Process(pid).children(recursive=True)]
    except psutil.Error:return []
def window(pid):
    ids={p.pid for p in family(pid)};found=[]
    @CALLBACK
    def enum(hwnd,param):
        proc=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(proc))
        text=ctypes.create_unicode_buffer(256);user.GetWindowTextW(hwnd,text,256)
        if proc.value in ids and user.IsWindowVisible(hwnd) and text.value=='AuroraLauncher':found.append(hwnd)
        return True
    user.EnumWindows(enum,0);return found[0] if found else None
def cpu(pid):
    value=0
    for p in family(pid):
        try:t=p.cpu_times();value+=t.user+t.system
        except psutil.Error:pass
    return value
def sample(pid,seconds):
    start=time.perf_counter();before=cpu(pid);time.sleep(seconds)
    elapsed=time.perf_counter()-start;working=private=0
    for p in family(pid):
        try:
            info=p.memory_info();working+=info.rss;private+=getattr(info,'private',info.rss)
        except psutil.Error:pass
    return {'cpu_one_core_percent':round((cpu(pid)-before)/elapsed*100,2),'working_set_mib':round(working/1048576,2),'private_mib':round(private/1048576,2)}

def run(exe,root,label):
    root.mkdir(parents=True,exist_ok=True)
    (root/'settings.json').write_text(json.dumps({'autoUpdate':False,'setupCompleted':True,'windowWidth':1280,'windowHeight':800}),encoding='utf-8')
    times=[];result={}
    for trial in range(2):
        begin=time.perf_counter();p=subprocess.Popen([str(exe),'--data-dir',str(root)])
        try:
            hwnd=None;deadline=time.monotonic()+45
            while not hwnd and time.monotonic()<deadline:
                if p.poll() is not None:raise RuntimeError(label+' exited before showing its window')
                hwnd=window(p.pid);time.sleep(.03)
            if not hwnd:raise RuntimeError(label+' startup timed out')
            times.append(round(time.perf_counter()-begin,3))
            if trial==1:
                user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd);time.sleep(2)
                result['foreground']=sample(p.pid,5)
                user.ShowWindow(hwnd,6);time.sleep(1)
                result['minimized']=sample(p.pid,5)
        finally:
            for proc in reversed(family(p.pid)):
                try:proc.terminate()
                except psutil.Error:pass
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()
    result['startup_seconds']=times;result['startup_mean_seconds']=round(statistics.mean(times),3)
    return result

if __name__=='__main__':
    baseline,current,out=map(Path,sys.argv[1:4]);root=Path(os.environ['RUNNER_TEMP'])/'aurora-performance'
    report={'machine':os.environ.get('RUNNER_OS'),'method':'Two launches each; same VM, 1280x800, 5s foreground and minimized samples. CPU is one logical core; includes child processes. Disk cache and CI variability apply.'}
    report['before_6_1_0']=run(baseline,root/'before','baseline')
    report['after_6_2_0']=run(current,root/'after','current')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps(report,indent=2))
