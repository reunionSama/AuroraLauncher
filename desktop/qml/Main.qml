// Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import Aurora 1.0

ApplicationWindow {
    id: root
    objectName: "auroraWindow"
    width: Math.min(1280, Screen.desktopAvailableWidth > 0 ? Screen.desktopAvailableWidth-48 : 1280); height: Math.min(800, Screen.desktopAvailableHeight > 0 ? Screen.desktopAvailableHeight-48 : 800); minimumWidth: 960; minimumHeight: 620
    visible: true; title: "AuroraLauncher"
    color: bg
    property string page: "home"
    property bool toolbarLabelsFit: {
        for(var i=0;i<quickNavRepeater.count;i++) {
            var button=quickNavRepeater.itemAt(i)
            if(!button || button.contentItem.truncated) return false
        }
        return true
    }
    property var cfg: backend.settings
    property var run: backend.runtime
    property bool reducedMotion: cfg.reduceMotion === true
    property bool dark: cfg.theme !== "light"
    property color bg: dark ? "#0c1823" : "#edf4f6"
    property color panel: dark ? "#142632" : "#ffffff"
    property color panel2: dark ? "#1c3442" : "#e5eff1"
    property color ink: dark ? "#e6f4f5" : "#172e38"
    property color muted: dark ? "#8faeba" : "#597581"
    property color accent: "#38cbbd"
    property color line: dark ? "#28424f" : "#d5e4e9"
    property var pages: [ {key:"home",label:"主页",icon:"⌂"},{key:"versions",label:"版本管理",icon:"▣"},{key:"resources",label:"资源中心",icon:"◇"},{key:"instances",label:"实例与存档",icon:"▤"},{key:"accounts",label:"账号管理",icon:"◎"},{key:"multiplayer",label:"多人联机",icon:"♧"},{key:"downloads",label:"下载任务",icon:"↓"},{key:"tools",label:"工具中心",icon:"✧"},{key:"logs",label:"实时日志",icon:"≡"},{key:"settings",label:"个性化设置",icon:"⚙"},{key:"about",label:"关于",icon:"ⓘ"} ]
    property var titles: ({home:"主页",versions:"版本管理",resources:"资源中心",instances:"实例与存档",accounts:"账号管理",multiplayer:"陶瓦多人联机",downloads:"下载任务",tools:"工具中心",logs:"实时日志",settings:"设置",about:"关于"})
    Component.onCompleted: {
        if(cfg.windowWidth>0) root.width=Math.min(Math.max(minimumWidth,cfg.windowWidth),Screen.desktopAvailableWidth)
        if(cfg.windowHeight>0) root.height=Math.min(Math.max(minimumHeight,cfg.windowHeight),Screen.desktopAvailableHeight-36)
    }
    onClosing: if(visibility===Window.Windowed) backend.rememberWindow(width,height)
    Shortcut{sequence:"Ctrl+1";onActivated:root.navigate("home")}
    Shortcut{sequence:"Ctrl+L";onActivated:root.navigate("logs")}
    Shortcut{sequence:"Ctrl+,";onActivated:root.navigate("settings")}
    font.family: appFont; font.pixelSize: 14
    palette.windowText: ink; palette.text: ink; palette.buttonText: ink
    palette.window: panel; palette.base: panel2; palette.button: panel2; palette.highlight: accent
    function navigate(target) {
        page=target
        if(target==="resources") { backend.listFiles("mods"); if(backend.modResults.length===0) backend.searchMods("","mod") }
        if(target==="tools") backend.preflight()
        if(target==="instances") backend.refresh()
    }
    function indexFor(model,key,value) { for(var i=0;i<model.length;i++) if(model[i][key]===value) return i; return -1 }
    function notice(title,message) { infoDialog.title=title;infoText.text=message;infoDialog.open() }
    component AButton: Button {
        id: b
        property bool primary: false
        implicitHeight: 42; implicitWidth: Math.max(92, Math.ceil(contentItem.implicitWidth)+40)
        padding: 12; leftPadding: 17; rightPadding: 17
        scale: down ? 0.97 : 1
        Behavior on scale { NumberAnimation { duration:root.reducedMotion?0:110; easing.type:Easing.OutCubic } }
        font.family: appFont; font.pixelSize: 14
        contentItem: Text { text:b.text; font:b.font; color:b.enabled ? (b.primary ? "#063b39" : root.ink) : root.muted; opacity:b.enabled?1:.45; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight }
        background: Rectangle { radius: 21; color:b.primary ? (b.down?"#23a99e":b.hovered?"#79e2d5":root.accent) : (b.down?root.line:b.hovered?root.line:root.panel2); opacity:b.enabled?1:.55; Behavior on color { ColorAnimation { duration: root.reducedMotion?0:130 } } }
    }
    component Field: TextField {
        id: field
        implicitHeight: 44; color: root.ink; placeholderTextColor: root.muted; selectByMouse: true; font.family:appFont; font.pixelSize:14; leftPadding:14; rightPadding:14
        background: Rectangle { radius:12; color:root.dark?"#0d1e2b":"#f6f9fa"; border.color:field.activeFocus?root.accent:root.line; border.width:1 }
    }
    component Select: ComboBox {
        id: sel
        implicitHeight:root.height<740?36:44; textRole:"text"; font.family:appFont; font.pixelSize:14
        contentItem: Text { text:sel.displayText; font:sel.font; color:root.ink; leftPadding:14; rightPadding:30; verticalAlignment:Text.AlignVCenter; elide:Text.ElideRight }
        background: Rectangle { color:root.panel2; radius:12; border.color:sel.activeFocus?root.accent:root.line }
        delegate: ItemDelegate { width:sel.width; text:sel.textRole ? modelData[sel.textRole] : modelData; highlighted:sel.highlightedIndex===index; font.family:appFont; palette.text:root.ink; palette.highlight:root.panel2; background:Rectangle{color:parent.highlighted?root.panel2:root.panel} }
        popup: Popup { y:sel.height+5; width:sel.width; padding:4; implicitHeight:Math.min(360,contentItem.implicitHeight+8); contentItem:ListView{clip:true;implicitHeight:contentHeight;model:sel.popup.visible?sel.delegateModel:null;currentIndex:sel.highlightedIndex;ScrollIndicator.vertical:ScrollIndicator{}} background:Rectangle{color:root.panel;radius:12;border.color:root.line} }
    }
    component LabelText: Text { color:root.ink; font.family:appFont; font.pixelSize:14; wrapMode:Text.Wrap }
    component MutedText: Text { color:root.muted; font.family:appFont; font.pixelSize:12; wrapMode:Text.Wrap }
    component Heading: Text { color:root.ink; font.family:appFont; font.pixelSize:24; font.bold:true }
    component Card: Rectangle {
        default property alias content: cardBody.data
        property alias body: cardBody
        color:root.panel; radius:20; border.color:root.line; implicitHeight:cardBody.implicitHeight+36
        ColumnLayout { id:cardBody; anchors.fill:parent;anchors.margins:18;spacing:12 }
    }
    header: Rectangle {
        height:root.height<700?60:70; color:root.panel
        RowLayout {
            anchors.fill:parent; anchors.leftMargin:24;anchors.rightMargin:20;spacing:12
            Image { source:assetBase+"/icon.png";Layout.preferredWidth:38;Layout.preferredHeight:38;MouseArea{anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:root.navigate("home")} }
            ColumnLayout { spacing:0;LabelText{text:"AuroraLauncher";font.pixelSize:21;font.bold:true} MutedText{text:root.page==="home"?"让每次出发更从容":"设置与工作区 / "+root.titles[root.page];font.pixelSize:11} }
            Item { Layout.fillWidth:true }
            Repeater {
                id:quickNavRepeater
                model:[{p:"versions",t:"▣  版本"},{p:"resources",t:"◇  资源"},{p:"accounts",t:"◎  账号"},{p:"downloads",t:"↓  下载"},{p:"settings",t:"⚙  设置"}]
                delegate:AButton { required property var modelData; objectName:"quickNav_"+modelData.p;text:root.width<1100?modelData.t.split("  ")[0]:modelData.t;implicitWidth:root.width<1100?56:104;primary:root.page===modelData.p;ToolTip.visible:hovered;ToolTip.text:modelData.t;onClicked:root.navigate(modelData.p) }
            }
        }
    }
    RowLayout {
        anchors.fill:parent;spacing:0
        Rectangle {
            visible:root.page!=="home";Layout.preferredWidth:root.width<1100?168:190;Layout.fillHeight:true;color:root.panel
            ColumnLayout {
                anchors.fill:parent;anchors.margins:12;spacing:5
                Repeater { model:root.pages
                    delegate:Button {
                        required property var modelData
                        Layout.fillWidth:true;implicitHeight:44;leftPadding:14
                        contentItem:LabelText{text:modelData.icon+"    "+modelData.label;verticalAlignment:Text.AlignVCenter;color:root.page===modelData.key?root.accent:root.ink}
                        background:Rectangle{radius:13;color:root.page===modelData.key?root.panel2:"transparent"}
                        onClicked:root.navigate(modelData.key)
                    }
                }
                Item{Layout.fillHeight:true}
                MutedText{text:"Aurora Desktop "+backend.version;Layout.fillWidth:true;horizontalAlignment:Text.AlignHCenter}
            }
        }
        Loader {
            id: pageLoader;objectName:"pageLoader";Layout.fillWidth:true;Layout.fillHeight:true
            onLoaded: if(!root.reducedMotion) pageEnter.restart()
            NumberAnimation { id:pageEnter;target:pageLoader;property:"opacity";from:0.2;to:1;duration:180;easing.type:Easing.OutCubic }
            sourceComponent: root.page==="home"?homePage:root.page==="versions"?versionsPage:root.page==="resources"?resourcesPage:root.page==="accounts"?accountsPage:root.page==="instances"?instancesPage:root.page==="multiplayer"?multiplayerPage:root.page==="downloads"?downloadsPage:root.page==="tools"?toolsPage:root.page==="logs"?logsPage:root.page==="settings"?settingsPage:aboutPage
        }
    }
    footer: Rectangle {
        visible:run.busy||run.running;height:visible?48:0;color:root.panel
        RowLayout {
            anchors.fill:parent;anchors.leftMargin:20;anchors.rightMargin:20;spacing:14
            BusyIndicator { running:run.busy;visible:run.busy;Layout.preferredWidth:24;Layout.preferredHeight:24 }
            LabelText { text:run.status;Layout.fillWidth:true;elide:Text.ElideRight;maximumLineCount:1 }
            ProgressBar { visible:run.busy;Layout.preferredWidth:240;value:Math.max(0,run.progress);indeterminate:run.progress<0 }
            AButton { text:run.running?"查看实时日志":"查看下载";implicitHeight:34;onClicked:root.navigate(run.running?"logs":"downloads") }
            AButton { visible:run.busy;text:"取消";implicitHeight:34;onClicked:backend.cancelTask() }
        }
    }
    Component {
        id:homePage
        Item {
            objectName:"homePage"
            AuroraView { id:sky;objectName:"auroraSky";anchors.fill:parent;visible:cfg.sky;renderActive:root.page==="home"&&root.active&&root.visibility!==Window.Minimized;fps:cfg.fps;brightness:cfg.brightness;speed:cfg.speed;hue:cfg.hue }
            RowLayout {
                anchors.fill:parent;anchors.margins:24;spacing:24
                Item {
                    Layout.fillWidth:true;Layout.fillHeight:true
                    ColumnLayout {
                        anchors.left:parent.left;anchors.top:parent.top;anchors.margins:18;spacing:12
                        Text { text:"A U R O R A";font.family:appFont;font.pixelSize:15;font.letterSpacing:4;color:"#84dfdb" }
                        Text { text:"把冒险，带到桌面。";font.family:appFont;font.pixelSize:36;font.bold:true;color:"#efffff" }
                        Text { text:"你的版本、世界与朋友，在这里再次相遇。";font.family:appFont;font.pixelSize:15;color:"#b3d4dc" }
                    }
                    RowLayout {
                        anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;spacing:12
                        Repeater {
                            model:[{title:"我的工作台",sub:"启动检查 · 诊断 · 实时日志",p:"tools"},{title:"相约同一世界",sub:"陶瓦联机 · 邀请你的朋友",p:"multiplayer"},{title:"极光与个性化",sub:"光幕 · 皮肤 · 人物动作",p:"settings"}]
                            delegate:Rectangle {
                                required property var modelData
                                Layout.fillWidth:true;Layout.preferredHeight:100;radius:18;color:tileMouse.containsMouse?"#d0264656":"#c017303f";border.color:"#3a6674"
                                ColumnLayout {anchors.fill:parent;anchors.margins:16;spacing:6;Text{text:modelData.title;color:"#edffff";font.family:appFont;font.pixelSize:15;font.bold:true}Text{text:modelData.sub;color:"#a2c4cf";font.family:appFont;font.pixelSize:11;wrapMode:Text.Wrap;Layout.fillWidth:true}Item{Layout.fillHeight:true}}
                                MouseArea{id:tileMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:root.navigate(modelData.p)}
                            }
                        }
                    }
                }
                Rectangle {
                    Layout.preferredWidth:335;Layout.fillHeight:true;radius:28;color:root.dark?"#f0142937":"#f2f6fbfc";border.color:root.line
                    ColumnLayout {
                        anchors.fill:parent;anchors.margins:root.height<740?16:22;spacing:root.height<740?5:11
                        RowLayout {LabelText{text:"准备下一次冒险";font.bold:true;font.pixelSize:17}Item{Layout.fillWidth:true}AButton{text:"＋";implicitWidth:40;implicitHeight:36;onClicked:root.navigate("accounts")}}
                        Item {
                            Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:root.height<740?95:185
                            PlayerView {id:player;objectName:"playerPreview";anchors.fill:parent;skinPath:backend.skinPath;skinModel:backend.skinModel;fps:cfg.fps;actions:cfg.actions;interval:cfg.interval;renderActive:root.page==="home"&&root.active&&root.visibility!==Window.Minimized}
                            MouseArea {anchors.fill:parent;property real lastX:0;property bool dragged:false;cursorShape:pressed?Qt.ClosedHandCursor:Qt.OpenHandCursor;onPressed:mouse=>{lastX=mouse.x;dragged=false}onPositionChanged:mouse=>{if(pressed){var d=mouse.x-lastX;if(Math.abs(d)>1)dragged=true;player.yawAngle+=d*.012;lastX=mouse.x}}onClicked:if(!dragged)player.triggerAction()}
                        }
                        MutedText {text:"左右拖动旋转 · 点击人物互动 · 20 种动作";Layout.fillWidth:true;horizontalAlignment:Text.AlignHCenter;font.pixelSize:10}
                        MutedText{text:backend.skinStatus;Layout.fillWidth:true;maximumLineCount:1;elide:Text.ElideRight;horizontalAlignment:Text.AlignHCenter;font.pixelSize:10}
                        LabelText{text:"玩家账号";font.pixelSize:12;color:root.muted}
                        Select {objectName:"accountSelector";Layout.fillWidth:true;model:backend.accountList;textRole:"name";currentIndex:root.indexFor(backend.accountList,"id",cfg.selectedAccount);displayText:currentIndex<0?"添加微软 / 离线账号":currentText;onActivated:backend.selectAccount(backend.accountList[currentIndex].id)}
                        LabelText{visible:root.height>=740;text:"独立实例";font.pixelSize:12;color:root.muted}
                        Select {visible:root.height>=740;Layout.fillWidth:true;model:backend.instances;textRole:"name";enabled:!run.busy&&!run.running;currentIndex:root.indexFor(backend.instances,"id",cfg.selectedInstance);onActivated:backend.selectInstance(backend.instances[currentIndex].id)}
                        LabelText{text:"游戏版本";font.pixelSize:12;color:root.muted}
                        Select {objectName:"versionSelector";Layout.fillWidth:true;model:backend.localVersions;textRole:"id";enabled:!run.busy&&!run.running;currentIndex:root.indexFor(backend.localVersions,"id",cfg.selectedVersion);displayText:currentIndex<0?"请先安装一个版本":currentText;onActivated:backend.setSetting("selectedVersion",backend.localVersions[currentIndex].id)}
                        AButton {objectName:"launchButton";text:run.running?"游戏运行中 · 查看日志":run.busy?"正在准备…":"启动游戏";primary:true;Layout.fillWidth:true;implicitHeight:55;enabled:!run.busy;onClicked:run.running?root.navigate("logs"):backend.launch()}
                        AButton {text:"安装新版本";Layout.fillWidth:true;implicitHeight:36;onClicked:root.navigate("versions")}
                    }
                }
            }
        }
    }
    Component {
        id:versionsPage
        ColumnLayout {
            objectName:"versionsPage";anchors.fill:parent;anchors.margins:24;spacing:16
            RowLayout {Heading{text:"版本管理"}Item{Layout.fillWidth:true}AButton{text:"复用已有游戏目录";enabled:!run.busy;onClicked:backend.chooseFile("library")}AButton{text:"刷新列表";onClicked:backend.fetchVersions()}}
            RowLayout {
                Layout.fillWidth:true;spacing:16
                Card {
                    Layout.preferredWidth:300;Layout.fillHeight:true
                    LabelText{text:"已安装版本";font.bold:true;font.pixelSize:17}
                    ListView {
                        id:localView;objectName:"localVersionList";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:8;model:backend.localVersions
                        delegate:Rectangle {required property var modelData;width:localView.width;height:88;radius:12;color:cfg.selectedVersion===modelData.id?root.line:root.panel2
                            ColumnLayout{anchors.fill:parent;anchors.margins:12;spacing:4;LabelText{text:modelData.id;font.bold:true;Layout.fillWidth:true;elide:Text.ElideMiddle;maximumLineCount:1}MutedText{text:modelData.loader+" · "+modelData.base} }
                            MouseArea{anchors.fill:parent;cursorShape:Qt.PointingHandCursor;enabled:!run.busy&&!run.running;onClicked:backend.setSetting("selectedVersion",modelData.id)}
                        }
                        LabelText{anchors.centerIn:parent;visible:backend.localVersions.length===0;text:"还没有安装版本\n从右侧选择一个开始";horizontalAlignment:Text.AlignHCenter;color:root.muted}
                        ScrollBar.vertical:ScrollBar{}
                    }
                    AButton{text:"校验 / 修复所选版本";Layout.fillWidth:true;enabled:!run.busy&&!run.running;onClicked:backend.repairVersion()}
                    AButton{text:"打开版本目录";Layout.fillWidth:true;onClicked:backend.openFolder("library")}
                }
                Card {
                    Layout.fillWidth:true;Layout.fillHeight:true
                    RowLayout {
                        Layout.fillWidth:true
                        Field{id:versionSearch;objectName:"versionSearch";Layout.fillWidth:true;placeholderText:"搜索版本，例如 1.21.1 / 1.20.1";onTextEdited:backend.filterVersions(text,snapshotToggle.checked)}
                        CheckBox{id:snapshotToggle;text:"快照";checked:false;palette.windowText:root.ink;onToggled:backend.filterVersions(versionSearch.text,checked)}
                        Select{id:loaderSelect;Layout.preferredWidth:115;model:["原版","Fabric","Forge","Quilt","NeoForge"];textRole:""}
                    }
                    MutedText{text:"安装文件共用，模组和存档按实例隔离。Java 会按版本自动准备。";Layout.fillWidth:true}
                    ListView {
                        id:remoteView;objectName:"remoteVersionList";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:8;model:backend.versions
                        delegate:Rectangle {required property var modelData;width:remoteView.width;height:78;color:root.panel2;radius:12
                            RowLayout {anchors.fill:parent;anchors.margins:13;spacing:12;ColumnLayout{Layout.fillWidth:true;spacing:4;LabelText{text:modelData.id;font.bold:true;font.pixelSize:17}MutedText{text:(modelData.type==="release"?"正式版":"快照 / 历史版")+" · "+modelData.date}}AButton{text:modelData.installed&&loaderSelect.currentIndex===0?"已安装":"安装";primary:!modelData.installed;enabled:!run.busy;onClicked:backend.installVersion(modelData.id,["vanilla","fabric","forge","quilt","neoforge"][loaderSelect.currentIndex])} }
                        }
                        LabelText{anchors.centerIn:parent;visible:backend.versions.length===0;text:run.catalogLoading?"正在获取版本列表…":"没有匹配版本，可刷新或调整搜索";color:root.muted}
                        ScrollBar.vertical:ScrollBar{}
                    }
                }
            }
        }
    }
    Component {
        id:resourcesPage
        ColumnLayout {
            objectName:"resourcesPage";anchors.fill:parent;anchors.margins:24;spacing:16
            property var kinds:["mod","resourcepack","shader","modpack"]
            property var folders:["mods","resourcepacks","shaderpacks","mods"]
            RowLayout{Heading{text:"资源中心"}Item{Layout.fillWidth:true}MutedText{text:"Modrinth · 按所选游戏版本与加载器匹配"}AButton{text:"导入整合包";enabled:!run.busy;onClicked:backend.chooseFile("pack")}}
            RowLayout {
                Layout.fillWidth:true
                Select {id:resourceKind;Layout.preferredWidth:135;model:["模组","资源包","光影","整合包"];textRole:"";onActivated:{backend.listFiles(parent.parent.folders[currentIndex]);backend.searchMods(modSearch.text,parent.parent.kinds[currentIndex])}}
                Field{id:modSearch;objectName:"modSearch";Layout.fillWidth:true;placeholderText:"搜索模组、整合包、资源包或光影";onAccepted:backend.searchMods(text,parent.parent.kinds[resourceKind.currentIndex])}
                AButton{text:"搜索";primary:true;onClicked:backend.searchMods(modSearch.text,parent.parent.kinds[resourceKind.currentIndex])}
            }
            RowLayout {
                Layout.fillWidth:true;Layout.fillHeight:true;spacing:16
                Card {
                    Layout.fillWidth:true;Layout.fillHeight:true
                    ListView {id:modList;objectName:"modResultList";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:10;model:backend.modResults
                        delegate:Rectangle {required property var modelData;width:modList.width;height:124;color:root.panel2;radius:13
                            RowLayout{anchors.fill:parent;anchors.margins:14;spacing:14
                                ColumnLayout{Layout.fillWidth:true;spacing:6;LabelText{text:modelData.title;font.bold:true;font.pixelSize:17;Layout.fillWidth:true;elide:Text.ElideRight;maximumLineCount:1}MutedText{text:modelData.description;Layout.fillWidth:true;maximumLineCount:2;elide:Text.ElideRight}MutedText{text:modelData.author+" · "+Number(modelData.downloads).toLocaleString(Qt.locale("zh_CN"))+" 次下载"}}
                                AButton{text:"安装";primary:true;enabled:!run.busy;onClicked:backend.installMod(modelData.id,modelData.kind)}
                            }
                        }
                        MutedText{anchors.centerIn:parent;visible:backend.modResults.length===0;text:"输入关键词并搜索\n需要的依赖会一并下载";horizontalAlignment:Text.AlignHCenter}
                        ScrollBar.vertical:ScrollBar{}
                    }
                }
                Card {
                    visible:resourceKind.currentIndex!==3;Layout.preferredWidth:285;Layout.fillHeight:true
                    LabelText{text:"当前实例资源";font.bold:true;font.pixelSize:16}
                    MutedText{text:backend.currentInstanceName;Layout.fillWidth:true}
                    RowLayout {AButton{text:"导入本地";enabled:!run.running;onClicked:backend.chooseFile(["mod","resourcepack","shader"][resourceKind.currentIndex])}AButton{text:"打开目录";onClicked:backend.openFolder(["mods","resourcepacks","shaderpacks"][resourceKind.currentIndex])}}
                    ListView {id:installedMods;Layout.fillWidth:true;Layout.fillHeight:true;model:backend.localFiles;clip:true;spacing:8
                        delegate:Rectangle {required property var modelData;width:installedMods.width;height:75;color:root.panel2;radius:10
                            ColumnLayout{anchors.fill:parent;anchors.margins:10;spacing:5;LabelText{text:modelData.name;Layout.fillWidth:true;elide:Text.ElideMiddle;maximumLineCount:1;font.pixelSize:12}RowLayout{MutedText{text:modelData.size+" MiB";Layout.fillWidth:true}AButton{visible:resourceKind.currentIndex===0;text:modelData.enabled?"停用":"启用";implicitHeight:25;implicitWidth:56;enabled:!run.running&&!run.busy;onClicked:backend.toggleMod(modelData.name)}}}
                        }ScrollBar.vertical:ScrollBar{}
                    }
                }
            }
        }
    }
    Component {
        id:accountsPage
        ColumnLayout {
            objectName:"accountsPage";anchors.fill:parent;anchors.margins:24;spacing:18
            Heading{text:"账号管理"}
            RowLayout {Layout.fillWidth:true;Layout.fillHeight:true;spacing:18
                Card {Layout.fillWidth:true;Layout.fillHeight:true
                    LabelText{text:"你的玩家档案";font.bold:true;font.pixelSize:18}
                    ListView{id:accountView;objectName:"accountList";Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:10;model:backend.accountList
                        delegate:Rectangle{required property var modelData;width:accountView.width;height:94;radius:14;color:cfg.selectedAccount===modelData.id?root.line:root.panel2
                            RowLayout{anchors.fill:parent;anchors.margins:16;ColumnLayout{Layout.fillWidth:true;LabelText{text:modelData.name;font.pixelSize:21;font.bold:true}MutedText{text:modelData.kind==="microsoft"?"微软正版账号":"本地离线账号"}}AButton{text:cfg.selectedAccount===modelData.id?"当前账号":"使用";onClicked:backend.selectAccount(modelData.id)}AButton{text:"移除";enabled:!run.busy;onClicked:backend.removeAccount(modelData.id)}}
                        }ScrollBar.vertical:ScrollBar{}
                    }
                }
                Card {Layout.preferredWidth:350;Layout.fillHeight:true
                    LabelText{text:"添加账号";font.bold:true;font.pixelSize:18}
                    MutedText{text:"微软登录会在浏览器完成授权，启动器不会收集你的微软密码。";Layout.fillWidth:true}
                    AButton{objectName:"microsoftLoginButton";text:"使用微软账号登录";primary:true;Layout.fillWidth:true;enabled:!run.busy;onClicked:backend.microsoftLogin()}
                    Rectangle{Layout.fillWidth:true;height:1;color:root.line}
                    LabelText{text:"本地离线档案";font.bold:true}
                    Field{id:offlineName;objectName:"offlineName";Layout.fillWidth:true;placeholderText:"3–16 位字母、数字或下划线";maximumLength:16;onAccepted:backend.addOffline(text)}
                    AButton{text:"添加离线账号";Layout.fillWidth:true;enabled:!run.busy;onClicked:backend.addOffline(offlineName.text)}
                    MutedText{text:"离线档案可用于本地游戏；需要正版验证的服务器请使用微软账号。";Layout.fillWidth:true}
                    Item{Layout.fillHeight:true}
                    AButton{text:"自定义人物皮肤";Layout.fillWidth:true;onClicked:backend.chooseFile("skin")}
                    AButton{objectName:"accountSkinButton";text:"使用 / 刷新账号皮肤";Layout.fillWidth:true;onClicked:backend.useAccountSkin()}
                    MutedText{text:backend.skinStatus;Layout.fillWidth:true}
                    MutedText{text:"微软账号令牌使用 Windows 当前用户加密保存。";Layout.fillWidth:true}
                }
            }
        }
    }
    Component {
        id:instancesPage
        ColumnLayout {
            objectName:"instancesPage";anchors.fill:parent;anchors.margins:24;spacing:16
            RowLayout{Heading{text:"实例与存档"}Item{Layout.fillWidth:true}AButton{text:"导入实例";enabled:!run.busy;onClicked:backend.importInstance()}AButton{text:"导出当前实例";enabled:!run.busy;onClicked:backend.exportInstance()}}
            RowLayout{Layout.fillWidth:true;Field{id:instanceName;placeholderText:"新实例名称，例如 生存世界 / 建筑 / 模组测试";Layout.fillWidth:true}AButton{text:"新建独立实例";primary:true;enabled:!run.busy&&!run.running;onClicked:backend.createInstance(instanceName.text)}}
            RowLayout {Layout.fillWidth:true;Layout.fillHeight:true;spacing:16
                Card{Layout.preferredWidth:280;Layout.fillHeight:true
                    LabelText{text:"我的实例";font.bold:true;font.pixelSize:17}
                    ListView{id:instanceList;Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:10;model:backend.instances
                        delegate:Rectangle{required property var modelData;width:instanceList.width;height:88;radius:12;color:cfg.selectedInstance===modelData.id?root.line:root.panel2;ColumnLayout{anchors.fill:parent;anchors.margins:14;LabelText{text:modelData.name;font.bold:true}MutedText{text:modelData.version||"尚未选择版本";Layout.fillWidth:true;elide:Text.ElideMiddle;maximumLineCount:1}}MouseArea{anchors.fill:parent;enabled:!run.busy&&!run.running;onClicked:backend.selectInstance(modelData.id)}}ScrollBar.vertical:ScrollBar{}}
                    AButton{text:"打开当前实例目录";Layout.fillWidth:true;onClicked:backend.openFolder("game")}
                }
                ColumnLayout{Layout.fillWidth:true;Layout.fillHeight:true;spacing:16
                    Card{Layout.fillWidth:true;Layout.preferredHeight:200
                        RowLayout{LabelText{text:backend.currentInstanceName+" · 备忘";font.bold:true;Layout.fillWidth:true}AButton{text:"保存";implicitHeight:32;onClicked:backend.saveNotes(instanceNotes.text)}}
                        ScrollView{Layout.fillWidth:true;Layout.fillHeight:true;TextArea{id:instanceNotes;text:backend.instanceNotes;placeholderText:"记录整合包注意事项、朋友的服务器地址、下次想做的事…";wrapMode:TextEdit.Wrap;color:root.ink;selectByMouse:true;font.family:appFont;background:Rectangle{color:root.panel2;radius:10}}}
                    }
                    Card{Layout.fillWidth:true;Layout.fillHeight:true
                        RowLayout{LabelText{text:"世界存档";font.bold:true;Layout.fillWidth:true}AButton{text:"恢复备份";implicitHeight:32;enabled:!run.busy;onClicked:backend.restoreWorld()}AButton{text:"打开目录";implicitHeight:32;onClicked:backend.openFolder("saves")}}
                        ListView{id:worldList;Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:8;model:backend.worlds
                            delegate:RowLayout{required property var modelData;width:worldList.width;height:46;LabelText{text:modelData.name;Layout.fillWidth:true}AButton{text:"备份";implicitHeight:32;enabled:!run.busy&&!run.running;onClicked:backend.backupWorld(modelData.name)}}
                            MutedText{anchors.centerIn:parent;visible:backend.worlds.length===0;text:"此实例还没有存档。"}ScrollBar.vertical:ScrollBar{}}
                    }
                }
            }
        }
    }
    Component {
        id:multiplayerPage
        ColumnLayout{
            objectName:"multiplayerPage";anchors.fill:parent;anchors.margins:24;spacing:18
            Heading{text:"陶瓦多人联机"}
            MutedText{text:"Terracotta © burningtnt 及贡献者 · 通过官方独立组件连接，不修改陶瓦程序。";Layout.fillWidth:true}
            RowLayout{Layout.fillWidth:true;spacing:18
                Card{Layout.fillWidth:true;Layout.preferredHeight:220
                    LabelText{text:"创建你的房间";font.bold:true;font.pixelSize:20}
                    MutedText{text:"先进入 Minecraft 存档，在暂停菜单选择“对局域网开放”，再创建房间。";Layout.fillWidth:true}
                    Item{Layout.fillHeight:true}
                    AButton{text:"创建房间";primary:true;Layout.fillWidth:true;enabled:!run.busy;onClicked:backend.terraAction("host","")}
                }
                Card{Layout.fillWidth:true;Layout.preferredHeight:220
                    LabelText{text:"加入朋友的世界";font.bold:true;font.pixelSize:20}
                    Field{id:roomCode;objectName:"roomCode";placeholderText:"粘贴陶瓦房间邀请码";Layout.fillWidth:true}
                    Item{Layout.fillHeight:true}
                    AButton{text:"加入房间";primary:true;Layout.fillWidth:true;enabled:!run.busy;onClicked:backend.terraAction("join",roomCode.text)}
                }
            }
            Card{Layout.fillWidth:true;Layout.fillHeight:true
                RowLayout{LabelText{text:run.roomState;font.bold:true;font.pixelSize:20;Layout.fillWidth:true}AButton{text:"离开 / 重置";onClicked:backend.terraAction("leave","")}}
                LabelText{text:run.room?"邀请码："+run.room:"房间就绪后会在这里显示邀请码。";font.pixelSize:17;Layout.fillWidth:true}
                RowLayout{AButton{visible:run.room!=="";text:"复制邀请码";onClicked:backend.copyText(run.room)}AButton{visible:run.roomAddress!=="";text:"启动并直连";onClicked:backend.launchServer(run.roomAddress)}LabelText{visible:run.roomAddress!=="";text:"直连地址："+run.roomAddress}}
                Flow{Layout.fillWidth:true;spacing:12;Repeater{model:run.roomMembers;delegate:LabelText{required property var modelData;text:"◎  "+modelData.name}}}
                Item{Layout.fillHeight:true}
                AButton{text:"陶瓦开源项目";onClicked:backend.openLink("terracotta")}
            }
        }
    }
    Component {
        id:downloadsPage
        ColumnLayout{
            objectName:"downloadsPage";anchors.fill:parent;anchors.margins:24;spacing:18
            RowLayout{Heading{text:"下载任务"}Item{Layout.fillWidth:true}AButton{text:"打开下载目录";onClicked:backend.openFolder("downloads")}AButton{text:"取消当前任务";visible:run.busy;onClicked:backend.cancelTask()}}
            Card{Layout.fillWidth:true;Layout.fillHeight:true
                ListView{id:taskList;Layout.fillWidth:true;Layout.fillHeight:true;model:backend.tasks;clip:true;spacing:12
                    delegate:Rectangle{required property var modelData;width:taskList.width;height:100;radius:14;color:root.panel2;ColumnLayout{anchors.fill:parent;anchors.margins:16;RowLayout{LabelText{text:modelData.title;Layout.fillWidth:true;elide:Text.ElideRight;maximumLineCount:1}MutedText{text:modelData.status}}ProgressBar{Layout.fillWidth:true;value:Math.max(0,modelData.progress);indeterminate:modelData.progress<0}}}
                    MutedText{anchors.centerIn:parent;visible:backend.tasks.length===0;text:"暂无下载任务。\n安装游戏、模组或整合包后会在这里显示。";horizontalAlignment:Text.AlignHCenter}ScrollBar.vertical:ScrollBar{}}
            }
        }
    }
    Component {
        id:toolsPage
        ColumnLayout{
            objectName:"toolsPage";anchors.fill:parent;anchors.margins:24;spacing:18
            Heading{text:"我的工作台"}
            RowLayout{Layout.fillWidth:true;spacing:12;AButton{text:"启动前检查";primary:true;onClicked:backend.preflight()}AButton{text:"网络诊断";onClicked:backend.networkDiagnostics()}AButton{text:"检测 Java";onClicked:backend.scanJava()}AButton{text:"实时日志";onClicked:root.navigate("logs")}AButton{text:"打开截图目录";onClicked:backend.openFolder("screenshots")}Item{Layout.fillWidth:true}}
            Card{Layout.fillWidth:true;Layout.fillHeight:true
                ListView{id:diagList;Layout.fillWidth:true;Layout.fillHeight:true;model:backend.diagnostics;clip:true;spacing:8
                    delegate:Rectangle{required property var modelData;width:diagList.width;height:72;radius:12;color:root.panel2;RowLayout{anchors.fill:parent;anchors.margins:15;Text{text:modelData.ok?"✓":"!";color:modelData.ok?root.accent:"#e8b988";font.pixelSize:23}ColumnLayout{Layout.fillWidth:true;LabelText{text:modelData.name;font.bold:true}MutedText{text:modelData.detail;Layout.fillWidth:true;elide:Text.ElideMiddle;maximumLineCount:1}}}}ScrollBar.vertical:ScrollBar{}}
            }
            Card{visible:backend.javaList.length>0;Layout.fillWidth:true;Layout.preferredHeight:150
                LabelText{text:"发现的 Java（点击设为自定义路径）";font.bold:true}
                ListView{id:javaView;Layout.fillWidth:true;Layout.fillHeight:true;model:backend.javaList;clip:true;delegate:ItemDelegate{required property var modelData;width:javaView.width;height:42;text:modelData.description+"  ·  "+modelData.path;palette.text:root.ink;onClicked:backend.setSetting("java",modelData.path)}ScrollBar.vertical:ScrollBar{}}
            }
        }
    }
    Component {
        id:logsPage
        ColumnLayout{
            objectName:"logsPage";anchors.fill:parent;anchors.margins:24;spacing:14
            RowLayout{Heading{text:"实时启动日志"}Item{Layout.fillWidth:true}CheckBox{id:followLog;text:"自动滚动";checked:true;palette.windowText:root.ink}AButton{text:"导出脱敏日志";onClicked:backend.exportLogs()}AButton{text:"打开日志目录";onClicked:backend.openFolder("logs")}AButton{visible:run.running;text:"停止游戏";onClicked:stopDialog.open()}}
            MutedText{text:run.running?"Minecraft 正在运行 · PID "+run.pid:"启动、下载和游戏输出会实时显示在这里。";Layout.fillWidth:true}
            Rectangle{Layout.fillWidth:true;Layout.fillHeight:true;radius:16;color:"#07121d";border.color:root.line
                ScrollView{id:logScroll;anchors.fill:parent;anchors.margins:15;clip:true
                    TextArea{id:logArea;objectName:"liveLogText";text:backend.logText;readOnly:true;selectByMouse:true;wrapMode:TextEdit.WrapAnywhere;color:"#bbd6df";font.family:appFont;font.pixelSize:12;background:null;onTextChanged:if(followLog.checked)Qt.callLater(function(){logArea.cursorPosition=logArea.length;logScroll.contentItem.contentY=Math.max(0,logArea.contentHeight-logScroll.availableHeight)})}
                }
            }
        }
    }
    Component {
        id:settingsPage
        ScrollView{
            id:settingsScroll;objectName:"settingsPage";anchors.fill:parent;anchors.margins:24;clip:true;contentWidth:availableWidth
            ColumnLayout{width:settingsScroll.availableWidth;spacing:18
                Heading{text:"让 Aurora 更像你的启动器"}
                Card{Layout.fillWidth:true
                    LabelText{text:"极光与人物";font.bold:true;font.pixelSize:18}
                    RowLayout{LabelText{text:"极光光幕";Layout.fillWidth:true}Switch{checked:cfg.sky;onToggled:backend.setSetting("sky",checked)}}
                    RowLayout{LabelText{text:"减少界面过渡动画";Layout.fillWidth:true}Switch{checked:root.reducedMotion;onToggled:backend.setSetting("reduceMotion",checked)}}
                    RowLayout{LabelText{text:"20 种随机人物动作";Layout.fillWidth:true}Switch{checked:cfg.actions;onToggled:backend.setSetting("actions",checked)}}
                    RowLayout{LabelText{text:"动作间隔："+cfg.interval+" 秒";Layout.preferredWidth:185}Slider{from:5;to:60;stepSize:1;value:cfg.interval;Layout.fillWidth:true;onMoved:backend.setSetting("interval",Math.round(value))}}
                    RowLayout{LabelText{text:"光幕亮度";Layout.preferredWidth:185}Slider{from:0;to:1;value:cfg.brightness;Layout.fillWidth:true;onMoved:backend.setSetting("brightness",value)}}
                    RowLayout{LabelText{text:"流动速度";Layout.preferredWidth:185}Slider{from:0;to:1;value:cfg.speed;Layout.fillWidth:true;onMoved:backend.setSetting("speed",value)}}
                    RowLayout{LabelText{text:"极光配色";Layout.preferredWidth:185}Slider{from:0;to:1;value:cfg.hue;Layout.fillWidth:true;onMoved:backend.setSetting("hue",value)}}
                    RowLayout{LabelText{text:"流畅 60 FPS（关闭为省电 30 FPS）";Layout.fillWidth:true}Switch{checked:cfg.fps===60;onToggled:backend.setSetting("fps",checked?60:30)}}
                    RowLayout{AButton{text:root.dark?"切换浅色外观":"切换深色外观";onClicked:backend.setSetting("theme",root.dark?"light":"dark")}AButton{text:"导入皮肤";onClicked:backend.chooseFile("skin")}AButton{text:"恢复账号皮肤";onClicked:backend.useAccountSkin()}Item{Layout.fillWidth:true}}
                }
                Card{Layout.fillWidth:true
                    LabelText{text:"游戏与下载";font.bold:true;font.pixelSize:18}
                    RowLayout{LabelText{text:"游戏内存："+cfg.memory+" MiB";Layout.preferredWidth:185}Slider{from:512;to:16384;stepSize:256;value:cfg.memory;Layout.fillWidth:true;onMoved:backend.setSetting("memory",Math.round(value/256)*256)}}
                    RowLayout{LabelText{text:"窗口大小";Layout.preferredWidth:185}Field{id:gameWidth;text:String(cfg.width);Layout.preferredWidth:110;validator:IntValidator{bottom:640;top:7680}onEditingFinished:if(acceptableInput)backend.setSetting("width",Number(text))}LabelText{text:"×"}Field{id:gameHeight;text:String(cfg.height);Layout.preferredWidth:110;validator:IntValidator{bottom:480;top:4320}onEditingFinished:if(acceptableInput)backend.setSetting("height",Number(text))}Item{Layout.fillWidth:true}}
                    RowLayout{LabelText{text:"并行下载："+cfg.workers+" 个";Layout.preferredWidth:185}Slider{from:2;to:32;stepSize:1;value:cfg.workers;Layout.fillWidth:true;enabled:!run.busy;onMoved:backend.setSetting("workers",Math.round(value))}}
                    RowLayout{LabelText{text:"下载源";Layout.preferredWidth:185}Select{Layout.preferredWidth:220;model:["自动选择 + 失败回退","官方优先","BMCLAPI 优先"];textRole:"";currentIndex:["auto","official","bmclapi"].indexOf(cfg.source);enabled:!run.busy;onActivated:backend.setSetting("source",["auto","official","bmclapi"][currentIndex])}Item{Layout.fillWidth:true}}
                    LabelText{text:"Java 路径（留空时自动选择对应版本）"}
                    RowLayout{Field{id:javaPath;Layout.fillWidth:true;text:cfg.java;placeholderText:"自动管理 Java 8 / 17 / 21";enabled:!run.busy;onEditingFinished:backend.setSetting("java",text)}AButton{text:"选择 Java";enabled:!run.busy;onClicked:backend.chooseFile("java")}AButton{text:"扫描";onClicked:backend.scanJava()}}
                    LabelText{text:"附加 JVM 参数"}
                    Field{Layout.fillWidth:true;text:cfg.jvmArgs;placeholderText:"例如 -XX:+UseG1GC";onEditingFinished:backend.setSetting("jvmArgs",text)}
                    RowLayout{AButton{text:"更换 / 导入游戏目录";enabled:!run.busy;onClicked:backend.chooseFile("library")}AButton{text:"打开游戏库";onClicked:backend.openFolder("library")}Item{Layout.fillWidth:true}}
                }
                Card{Layout.fillWidth:true
                    LabelText{text:"更新";font.bold:true;font.pixelSize:18}
                    RowLayout{LabelText{text:"打开启动器时检查 Windows 新版";Layout.fillWidth:true}Switch{checked:cfg.autoUpdate;onToggled:backend.setSetting("autoUpdate",checked)}}
                    AButton{text:"检查更新";onClicked:backend.checkUpdate(true)}
                }
                Item{Layout.preferredHeight:12}
            }
        }
    }
    Component {
        id:aboutPage
        ScrollView{id:aboutScroll;objectName:"aboutPage";anchors.fill:parent;anchors.margins:24;contentWidth:availableWidth;clip:true
            ColumnLayout{width:aboutScroll.availableWidth;spacing:20
                Rectangle{Layout.fillWidth:true;implicitHeight:280;radius:28;gradient:Gradient{orientation:Gradient.Horizontal;GradientStop{position:0;color:"#102b3b"}GradientStop{position:1;color:"#174d49"}}
                    ColumnLayout{anchors.fill:parent;anchors.margins:26;spacing:13
                        RowLayout{Image{source:assetBase+"/icon.png";Layout.preferredWidth:64;Layout.preferredHeight:64}ColumnLayout{Text{text:"AuroraLauncher";color:"#efffff";font.family:appFont;font.pixelSize:32;font.bold:true}Text{text:"让每次出发更从容 · Windows "+backend.version;color:"#9ee9df";font.family:appFont;font.pixelSize:14}}}
                        Text{text:"Aurora 项目维护：reunionSama\n极光主页 · 可旋转人物 · 20 种动作 · 独立实例 · Modrinth · 实时日志 · 陶瓦联机";color:"#e2f5f5";font.family:appFont;font.pixelSize:14;wrapMode:Text.Wrap;Layout.fillWidth:true}
                        Flow{Layout.fillWidth:true;spacing:10;AButton{text:"项目主页";onClicked:backend.openLink("project")}AButton{text:"手机版项目";onClicked:backend.openLink("mobile")}AButton{text:"检查更新";onClicked:backend.checkUpdate(true)}AButton{objectName:"sponsorButton";text:"赞助创作者";primary:true;onClicked:backend.openLink("sponsor")}}
                    }
                }
                Card{Layout.fillWidth:true
                    Heading{text:"技术来源与开源许可";font.pixelSize:20}
                    LabelText{text:"桌面界面与功能由 Aurora 项目重新实现，沿用 Aurora Android 的交互设计和人物动作公式。手机版基于 Zalith Launcher 2 / PojavLauncher；桌面版使用原生 Windows Java Edition 启动流程。";Layout.fillWidth:true}
                    MutedText{text:"Zalith Launcher 2：MovTery 及贡献者；PojavLauncher 及贡献者。Aurora 新增部分：reunionSama。整体桌面项目遵循 GPL-3.0-or-later，第三方组件保留各自许可。";Layout.fillWidth:true}
                    MutedText{text:"minecraft-launcher-lib © JakobDev（BSD-2-Clause）；Qt / PySide6 © The Qt Company（LGPL-3.0）；Terracotta © burningtnt 及贡献者（AGPL-3.0-or-later，独立进程集成例外）；Noto Sans CJK（SIL Open Font License）。AzureLauncher 仅作为功能流程参考，未复制其代码或图标。";Layout.fillWidth:true}
                    Flow{Layout.fillWidth:true;spacing:10;AButton{text:"查看完整许可";onClicked:backend.openLink("license")}AButton{text:"ZL2 开源项目";onClicked:backend.openLink("zl2")}AButton{text:"陶瓦联机源码";onClicked:backend.openLink("terracotta")}}
                }
                Item{Layout.preferredHeight:12}
            }
        }
    }
    Dialog{id:infoDialog;objectName:"infoDialog";anchors.centerIn:Overlay.overlay;width:Math.min(root.width-100,600);modal:true;standardButtons:Dialog.Ok;contentItem:ScrollView{implicitHeight:Math.min(infoText.implicitHeight+10,350);TextArea{id:infoText;width:parent.width;readOnly:true;selectByMouse:true;wrapMode:TextEdit.Wrap;font.family:appFont;color:root.ink;background:null}}background:Rectangle{color:root.panel;radius:22;border.color:root.line}}
    Dialog{id:loginDialog;objectName:"loginDialog";title:"微软账号登录";anchors.centerIn:Overlay.overlay;width:Math.min(540,root.width-48);modal:true;closePolicy:Popup.NoAutoClose;standardButtons:Dialog.Cancel;onRejected:{backend.cancelTask();close()}background:Rectangle{color:root.panel;radius:22;border.color:root.line}
        contentItem:ColumnLayout{spacing:16;LabelText{text:"在微软网页输入以下设备码，完成账号授权。";Layout.fillWidth:true}Text{text:run.authCode;font.family:appFont;font.pixelSize:38;font.bold:true;color:root.accent;Layout.alignment:Qt.AlignHCenter}RowLayout{Layout.alignment:Qt.AlignHCenter;AButton{text:"复制设备码";onClicked:backend.copyText(run.authCode)}AButton{objectName:"openMicrosoftLoginButton";text:"打开微软登录网页";primary:true;onClicked:backend.openLoginPage()}}MutedText{text:"请在浏览器登录；设备码过期后可重新获取。";Layout.fillWidth:true}}
    }
    Dialog{id:updateDialog;title:run.updateTitle;anchors.centerIn:Overlay.overlay;width:Math.min(640,root.width-48);modal:true;standardButtons:Dialog.Cancel;background:Rectangle{color:root.panel;radius:22;border.color:root.line}contentItem:ColumnLayout{spacing:16;ScrollView{Layout.fillWidth:true;Layout.preferredHeight:300;TextArea{width:parent.width;text:run.updateBody;readOnly:true;wrapMode:TextEdit.Wrap;selectByMouse:true;color:root.ink;font.family:appFont;background:null}}AButton{text:"在应用内下载新版 EXE";primary:true;Layout.fillWidth:true;enabled:!run.busy;onClicked:{backend.downloadUpdate();updateDialog.close()}}}}
    Dialog{id:stopDialog;title:"停止 Minecraft？";anchors.centerIn:Overlay.overlay;modal:true;standardButtons:Dialog.Yes|Dialog.No;onAccepted:backend.stopGame();LabelText{text:"这会结束当前游戏进程，请先保存世界。"}}
    Connections {
        target:backend
        function onMessage(title,message){root.notice(title,message);if(!run.busy&&loginDialog.opened)loginDialog.close()}
        function onDeviceReady(code,url){loginDialog.open()}
        function onUpdateReady(title,body){updateDialog.open()}
        function onRuntimeChanged(){if(!backend.runtime.busy&&loginDialog.opened)loginDialog.close()}
    }
}
