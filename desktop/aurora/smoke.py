# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Real packaged-executable game smoke. Uses Minecraft's demo mode, never user credentials."""
import ctypes,json,os,sys,time
from pathlib import Path
from PySide6.QtCore import QTimer,QObject
from PySide6.QtGui import QGuiApplication
from .auth import offline

def game_smoke(app,root,backend,args):
    report={'ok':False,'platform':sys.platform,'frozen':bool(getattr(sys,'frozen',False)),'version':args.game_version,'mode':'demo','credentials_used':False,'game_window':False,'renderer_initialized':False}
    path=Path(args.test_report);path.parent.mkdir(parents=True,exist_ok=True);shots=Path(args.screenshot_dir or path.parent/'game-screens');shots.mkdir(parents=True,exist_ok=True)
    backend.store.settings.update(memory=1536,width=960,height=540,jvmArgs='-Dfile.encoding=UTF-8')
    if os.environ.get('JAVA_HOME'):backend.store.settings['java']=str(Path(os.environ['JAVA_HOME'])/'bin'/'java.exe')
    backend.store.save();root.setProperty('page','logs');state={'start':time.monotonic(),'launched':0,'finished':False,'pid':None}
    def work():
        v=backend.engine.install(args.game_version)
        return backend.engine.launch(v,offline('AuroraTester'),backend.store.game_dir(),backend._exited.emit,demo=True)
    backend.submit('game-smoke',work,True)
    def finish(error=''):
        if state['finished']:return
        state['finished']=True;timer.stop();report['seconds']=round(time.monotonic()-state['start'],2);report['error']=error
        report['ok']=not error and report['game_window'] and report['renderer_initialized']
        try:report['final_log']='\n'.join(backend._log)[-20000:]
        except Exception:pass
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
        backend.engine.stop();root.close();app.exit(0 if report['ok'] else 4)
    def poll():
        if state['finished']:return
        if time.monotonic()-state['start']>1000:finish('Game integration timeout');return
        p=backend.engine.process
        if p is None:
            if not backend.runtime['busy'] and 'game-smoke' not in backend._jobs:finish('Installation/launch failed; see launcher log')
            return
        if not state['launched']:state['launched']=time.monotonic();report['pid']=p.pid
        if p.poll() is not None:finish('Minecraft exited before the main menu, code '+str(p.returncode));return
        lines='\n'.join(backend._log)
        report['renderer_initialized']='Created:' in lines and ('OpenAL initialized' in lines or 'Sound engine started' in lines)
        if sys.platform=='win32':
            from ctypes import wintypes
            user=ctypes.windll.user32;found=[]
            callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
            def visit(hwnd,param):
                pid=wintypes.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
                if pid.value==p.pid and user.IsWindowVisible(hwnd):
                    title=ctypes.create_unicode_buffer(512);user.GetWindowTextW(hwnd,title,512)
                    if 'Minecraft' in title.value:found.append((hwnd,title.value))
                return True
            cb=callback(visit);user.EnumWindows(cb,0)
            if found and report['renderer_initialized'] and time.monotonic()-state['launched']>20:
                hwnd,title=found[0];user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd)
                report['window_title']=title;report['game_window']=True
                image=QGuiApplication.primaryScreen().grabWindow(int(hwnd))
                if image.isNull():finish('Game window exists, screenshot unavailable');return
                image.save(str(shots/'minecraft-demo.png'));finish()
        else:finish('This real-game smoke requires Windows')
    timer=QTimer(backend);timer.timeout.connect(poll);timer.start(800)
    return timer
