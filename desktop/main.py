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
    from aurora import VERSION
    from aurora.storage import Store
    from aurora.visuals import AuroraView,PlayerView
    from aurora.bridge import Bridge
    app=QApplication(sys.argv[:1]);app.setOrganizationName('reunionSama');app.setApplicationName('AuroraLauncher');app.setApplicationVersion(VERSION);app.setWindowIcon(QIcon(str(resources()/'assets/icon.ico')))
    QQuickStyle.setStyle('Basic')
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('reunionSama.AuroraLauncher.Desktop6')
    # Windows already has CJK fallback fonts; loading the 16 MiB bundled font
    # on every launch needlessly copies font tables and expands the glyph cache.
    font='Microsoft YaHei UI'
    if sys.platform!='win32':
        font_id=QFontDatabase.addApplicationFont(str(resources()/'assets/NotoSansCJKsc-Regular.otf'))
        families=QFontDatabase.applicationFontFamilies(font_id)
        if families:font=families[0]
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
    backend.setForeground(root.isActive())
    root.activeChanged.connect(lambda:backend.setForeground(root.isActive()))
    def ui(name):
        found=root.findChild(QObject,name)
        if found is not None:return found
        stack=[root.contentItem()];seen=set()
        for popup_name in ('installerDialog','setupWizard'):
            popup=root.findChild(QObject,popup_name)
            if popup is not None and popup.property('contentItem') is not None:stack.append(popup.property('contentItem'))
        import shiboken6
        while stack:
            item=stack.pop()
            address=shiboken6.getCppPointer(item)[0]
            if address in seen:continue
            seen.add(address)
            if item.objectName()==name:return item
            stack.extend(item.childItems())
        raise RuntimeError('Missing visual object '+name)
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
                page=pages[state['index']]
                if page=='resources':
                    backend._results=[{'id':'ui-icon-fixture','title':'UI icon check','description':'Local thumbnail fixture','downloads':1,'author':'Aurora','kind':'mod','icon':'','iconLocal':(resources()/'assets/icon.png').as_uri()}];backend.dataChanged.emit()
                root.setProperty('page',page)
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
                if page=='resources':report['project_icon']=bool(ui('projectIcon_ui-icon-fixture').property('iconReady'))
                if page=='about':report['sponsor_button']=root.findChild(QObject,'sponsorButton') is not None
                if page=='accounts':
                    from PySide6.QtGui import QDesktopServices
                    opened=[];original=QDesktopServices.openUrl
                    try:
                        QDesktopServices.openUrl=lambda url:opened.append(url.toString()) or True
                        backend._on_device('TEST-CODE','https://www.microsoft.com/link')
                        button=root.findChild(QObject,'openMicrosoftLoginButton')
                        if button is None:raise RuntimeError('Missing Microsoft login button')
                        button.clicked.emit()
                        report['microsoft_link_button']=opened==['https://www.microsoft.com/link']
                    finally:QDesktopServices.openUrl=original;backend._set(authCode='',authUrl='')
                state['index']+=1
                if state['index']<len(pages):QTimer.singleShot(70,check_page)
                else:
                    start_feature_checks()
            except Exception as e:finish(str(e))
        def start_feature_checks():
            backend._append_log('AURORA_UI_SEARCH alpha')
            backend._append_log('AURORA_UI_SEARCH beta')
            backend._flush_logs();root.setProperty('page','logs')
            QTimer.singleShot(200,set_log_query)
        def set_log_query():
            try:
                field=root.findChild(QObject,'logSearchField');field.setProperty('text','AURORA_UI_SEARCH')
                QTimer.singleShot(250,verify_log_search)
            except Exception as e:finish(str(e))
        def verify_log_search():
            try:
                count=root.findChild(QObject,'logSearchCount').property('text')
                report['log_search']=str(count).endswith('/ 2')
                root.grabWindow().save(str(shots/'log-search.png'))
                from aurora.installers import COMPONENTS
                from PySide6.QtCore import QMetaObject
                backend._installer={'minecraft':'1.20.1','rows':[{'kind':kind,'title':title,'status':'可以选择','choices':[{'id':'test-build','label':'UI fixture build'}],'loading':False} for kind,title in COMPONENTS]};backend.installerChanged.emit()
                dialog=root.findChild(QObject,'installerDialog');QMetaObject.invokeMethod(dialog,'open')
                report['installer_dialog']=bool(dialog.property('visible'));state['installer_dialog']=dialog
                QTimer.singleShot(160,select_fabric)
            except Exception as e:finish(str(e))
        def select_fabric():
            try:
                combo=ui('componentSelect_fabric');combo.setProperty('currentIndex',1);combo.activated.emit(1)
                QTimer.singleShot(180,verify_loader_exclusion)
            except Exception as e:finish(str(e))
        def verify_loader_exclusion():
            try:
                fabric=ui('componentSelect_fabric');forge=ui('componentSelect_forge')
                report['loader_exclusion']=fabric.property('currentIndex')==1 and not forge.property('enabled') and forge.property('currentIndex')==0
                root.grabWindow().save(str(shots/'installer.png'))
                ui('clearLoaderButton').clicked.emit()
                QTimer.singleShot(120,select_forge)
            except Exception as e:finish(str(e))
        def select_forge():
            try:
                combo=ui('componentSelect_forge');combo.setProperty('currentIndex',1);combo.activated.emit(1)
                QTimer.singleShot(150,close_installer)
            except Exception as e:finish(str(e))
        def close_installer():
            try:
                from PySide6.QtCore import QMetaObject
                fabric=ui('componentSelect_fabric');forge=ui('componentSelect_forge')
                report['loader_switch_resets']=fabric.property('currentIndex')==0 and not fabric.property('enabled') and forge.property('currentIndex')==1
                from aurora.installers import COMPONENTS
                report['loader_icons']=all(bool(ui('loaderIcon_'+kind).property('iconReady')) for kind,title in COMPONENTS)
                QMetaObject.invokeMethod(state.pop('installer_dialog'),'close')
                wizard=root.findChild(QObject,'setupWizard');QMetaObject.invokeMethod(wizard,'open');state['wizard']=wizard
                QTimer.singleShot(120,check_setup)
            except Exception as e:finish(str(e))
        def check_setup():
            try:
                wizard=state['wizard'];report['setup_wizard']=wizard.property('visible')
                root.grabWindow().save(str(shots/'setup-language.png'))
                ui('setupLanguage_en_US').clicked.emit()
                report['setup_language']=backend.settings['language']=='en_US'
                wizard.setProperty('step',1);QTimer.singleShot(120,capture_setup_theme)
            except Exception as e:finish(str(e))
        def capture_setup_theme():
            root.grabWindow().save(str(shots/'setup-theme.png'));state['wizard'].setProperty('step',2);QTimer.singleShot(120,skip_setup)
        def skip_setup():
            try:
                root.grabWindow().save(str(shots/'setup-account.png'))
                root.findChild(QObject,'setupSkip').clicked.emit()
                report['setup_skip']=not state.pop('wizard').property('visible') and backend.settings['setupCompleted'] and json.loads(store.file.read_text('utf-8'))['setupCompleted']
                state['language_index']=0;report['languages']={};test_language()
            except Exception as e:finish(str(e))
        def test_language():
            language=['zh_CN','en_US','ja_JP','ko_KR'][state['language_index']]
            backend.setSetting('language',language);root.setProperty('page','home')
            QTimer.singleShot(180,verify_language)
        def verify_language():
            try:
                language=backend.settings['language'];button=root.findChild(QObject,'launchButton')
                report['languages'][language]=button.property('text')==backend.translate('启动游戏')
                root.grabWindow().save(str(shots/('home-'+language+'.png')))
                root.setProperty('page','settings');QTimer.singleShot(180,capture_language_settings)
            except Exception as e:finish(str(e))
        def capture_language_settings():
            language=backend.settings['language'];root.grabWindow().save(str(shots/('settings-'+language+'.png')))
            state['language_index']+=1
            if state['language_index']<4:test_language()
            else:
                backend.setSetting('language','zh_CN');root.setProperty('page','home');root.setWidth(960);root.setHeight(620)
                from PySide6.QtGui import QImage,QColor
                cape=QImage(64,32,QImage.Format.Format_ARGB32);cape.fill(QColor('#e53d56'));cape_path=store.root/'test-preview-cape.png';cape.save(str(cape_path))
                backend._cape=str(cape_path);backend.dataChanged.emit()
                QTimer.singleShot(160,capture_cape)
        def capture_cape():
            try:
                player=root.findChild(QObject,'playerPreview');report['cape_preview_binding']=bool(player.property('capePath'))
                player.setProperty('yawAngle',3.14159);QTimer.singleShot(220,check_compact)
            except Exception as e:finish(str(e))
        def check_compact():
            try:
                from PySide6.QtCore import QPointF
                launch=root.findChild(QObject,'launchButton');bottom=launch.mapToScene(QPointF(0,launch.height())).y()
                report['compact_window']=bottom<=root.height()
                report['toolbar_labels_fit']=bool(root.property('toolbarLabelsFit'))
                root.grabWindow().save(str(shots/'compact.png'));finish()
            except Exception as e:finish(str(e))
        def finish(error=''):
            report['warnings']=errors;report['error']=error;report['ok']=not error and not errors and all(report['pages'].values()) and report.get('manual_rotation',False) and report.get('sponsor_button',False) and report.get('microsoft_link_button',False) and report.get('compact_window',False) and report.get('toolbar_labels_fit',False) and report.get('log_search',False) and report.get('installer_dialog',False) and report.get('cape_preview_binding',False) and all(report.get(key,False) for key in ('project_icon','loader_exclusion','loader_switch_resets','loader_icons','setup_wizard','setup_language','setup_skip')) and len(report.get('languages',{}))==4 and all(report.get('languages',{}).values())
            if report_path:report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
            root.close();app.exit(0 if report['ok'] else 3)
        root.setWidth(1280);root.setHeight(800)
        QTimer.singleShot(900,check_page)
        QTimer.singleShot(45000,lambda:finish('Self-test timeout') if not report['ok'] else None)
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

