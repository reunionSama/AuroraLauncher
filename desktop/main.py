# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
import argparse,json,os,sys,time,traceback
from pathlib import Path

def resources():return Path(getattr(sys,'_MEIPASS',Path(__file__).parent))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data-dir');parser.add_argument('--self-test',action='store_true');parser.add_argument('--test-report');parser.add_argument('--screenshot-dir');parser.add_argument('--software',action='store_true');parser.add_argument('--game-smoke',action='store_true');parser.add_argument('--game-version',default='1.20.1')
    args=parser.parse_args()
    if args.data_dir:os.environ['AURORA_HOME']=args.data_dir
    if args.software or args.self_test or args.game_smoke:os.environ['QT_QUICK_BACKEND']='software'
    from PySide6.QtCore import QUrl,QTimer,QObject
    from PySide6.QtGui import QIcon,QFontDatabase
    from PySide6.QtWidgets import QApplication
    from PySide6.QtQml import QQmlApplicationEngine,qmlRegisterType
    from PySide6.QtQuickControls2 import QQuickStyle
    from aurora.storage import Store
    from aurora.visuals import AuroraView,PlayerView
    from aurora.bridge import Bridge
    app=QApplication(sys.argv[:1]);app.setOrganizationName('reunionSama');app.setApplicationName('AuroraLauncher');app.setApplicationVersion('6.0.0');app.setWindowIcon(QIcon(str(resources()/'assets/icon.ico')))
    QQuickStyle.setStyle('Basic')
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('reunionSama.AuroraLauncher.Desktop6')
    font_id=QFontDatabase.addApplicationFont(str(resources()/'assets/NotoSansCJKsc-Regular.otf'))
    families=QFontDatabase.applicationFontFamilies(font_id);font=families[0] if families else 'Microsoft YaHei UI'
    qmlRegisterType(AuroraView,'Aurora',1,0,'AuroraView');qmlRegisterType(PlayerView,'Aurora',1,0,'PlayerView')
    store=Store();backend=Bridge(store,resources()/'assets',args.self_test or args.game_smoke)
    engine=QQmlApplicationEngine();context=engine.rootContext();context.setContextProperty('backend',backend);context.setContextProperty('appFont',font);context.setContextProperty('assetBase',QUrl.fromLocalFile(str(resources()/'assets')).toString())
    errors=[]
    def warnings(values):
        for w in values:errors.append(str(w))
    engine.warnings.connect(warnings)
    engine.load(QUrl.fromLocalFile(str(resources()/'qml/Main.qml')))
    report_path=Path(args.test_report) if args.test_report else None
    if not engine.rootObjects():
        if report_path:report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps({'ok':False,'errors':errors},ensure_ascii=False,indent=2),'utf-8')
        backend.close();return 2
    root=engine.rootObjects()[0]
    game_timer=None
    if args.game_smoke:
        from aurora.smoke import game_smoke
        game_timer=game_smoke(app,root,backend,args)
    if args.self_test:
        report={'ok':False,'platform':sys.platform,'frozen':bool(getattr(sys,'frozen',False)),'pages':{},'warnings':errors,'client_id':backend.clientId}
        shots=Path(args.screenshot_dir or store.root/'test-screenshots');shots.mkdir(parents=True,exist_ok=True)
        pages=['home','versions','resources','instances','accounts','multiplayer','downloads','tools','logs','settings','about'];state={'index':0}
        backend.addOffline('AuroraTester')
        def check_page():
            try:
                page=pages[state['index']];root.setProperty('page',page)
                QTimer.singleShot(260,capture)
            except Exception as e:finish(str(e))
        def capture():
            try:
                page=pages[state['index']];obj=root.findChild(QObject,page+'Page');report['pages'][page]=obj is not None
                if obj is None:raise RuntimeError('Missing page '+page)
                if page in ('home','accounts','settings','about'):
                    image=root.grabWindow()
                    if image.isNull():raise RuntimeError('Could not capture the window')
                    image.save(str(shots/(page+'.png')))
                if page=='home':
                    sky=root.findChild(QObject,'auroraSky');player=root.findChild(QObject,'playerPreview')
                    report['aurora_frames']=sky.property('frameCount');report['player_frames']=player.property('frameCount')
                    from PySide6.QtTest import QTest
                    from PySide6.QtCore import Qt,QPointF,QPoint
                    old=player.property('yawAngle');point=player.mapToScene(QPointF(player.width()/2,player.height()/2)).toPoint()
                    QTest.mousePress(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
                    QTest.mouseMove(root,point+QPoint(65,0),30)
                    QTest.mouseRelease(root,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point+QPoint(65,0))
                    report['manual_rotation']=abs(player.property('yawAngle')-old)>.1;player.triggerAction()
                if page=='about':report['sponsor_button']=root.findChild(QObject,'sponsorButton') is not None
                state['index']+=1
                if state['index']<len(pages):QTimer.singleShot(70,check_page)
                else:finish()
            except Exception as e:finish(str(e))
        def finish(error=''):
            report['warnings']=errors;report['error']=error;report['ok']=not error and all(report['pages'].values()) and report.get('manual_rotation',False) and report.get('sponsor_button',False)
            if report_path:report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
            root.close();app.exit(0 if report['ok'] else 3)
        root.setWidth(1280);root.setHeight(800)
        QTimer.singleShot(900,check_page)
        QTimer.singleShot(20000,lambda:finish('Self-test timeout') if not report['ok'] else None)
    code=app.exec()
    import shiboken6
    shiboken6.delete(engine)
    backend.close();return code

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        text=traceback.format_exc();path=Path(os.environ.get('AURORA_HOME',str(Path.home())))/'aurora-startup-error.log';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,'utf-8')
        if sys.stderr:print(text,file=sys.stderr)
        sys.exit(1)
