"""Aurora-owned UI additions; upstream feature routes, credits and engine remain."""
from pathlib import Path
import re
import shutil
import json


def apply(root):
    root = Path(root)
    module = root / 'ZalithLauncher'
    java = module / 'src/main/java/com/movtery/zalithlauncher'
    def edit(path, old, new):
        text = path.read_text()
        if text.count(old) != 1:
            raise RuntimeError(f'Expected one marker in {path}: {old[:90]}')
        path.write_text(text.replace(old, new, 1))
    overlay = Path(__file__).parent / 'overlay'
    dest = java / 'ui/screens/content/aurora'
    dest.mkdir(parents=True, exist_ok=True)
    for file in overlay.glob('*.kt'):
        shutil.copy2(file, dest / file.name)
    nav = java / 'ui/screens/NormalNavKey.kt'
    edit(nav, '@Serializable data object LauncherMain : NormalNavKey', '''@Serializable data object LauncherMain : NormalNavKey
    @Serializable data object AuroraTools : NormalNavKey {
        @Contextual override val title: AndroidStringText = androidText(R.string.aurora_tools)
    }''')
    main = java / 'ui/screens/main/MainScreen.kt'
    edit(main, 'import androidx.compose', 'import androidx.compose') if False else None
    edit(main, 'import com.movtery.zalithlauncher.ui.screens.content.SettingsScreen', 'import com.movtery.zalithlauncher.ui.screens.content.aurora.AuroraToolsScreen\nimport com.movtery.zalithlauncher.ui.screens.content.SettingsScreen')
    edit(main, '                toSettingsScreen = {', '''                toAuroraTools = {
                    screenBackStackModel.mainScreen.navigateTo(NormalNavKey.AuroraTools, useClassEquality = true)
                },
                toSettingsScreen = {''')
    edit(main, '    toSettingsScreen: () -> Unit,', '    toSettingsScreen: () -> Unit,\n    toAuroraTools: () -> Unit,')
    edit(main, '''                TopBarRailItem(
                    selected = inMultiplayerScreen,''', '''                TopBarRailItem(
                    selected = mainScreenKey is NormalNavKey.AuroraTools,
                    painter = painterResource(R.drawable.ic_rocket_launch_filled),
                    text = stringResource(R.string.aurora_tools),
                    onClick = toAuroraTools
                )

                TopBarRailItem(
                    selected = inMultiplayerScreen,''')
    entry = '''                entry<NormalNavKey.AuroraTools> {
                    AuroraToolsScreen(
                        currentKey = screenBackStackModel.mainScreen.currentKey,
                        onLaunch = { eventViewModel.sendEvent(EventViewModel.Event.Launch.Game(VersionsManager.currentVersion.value)) },
                        onOpenLog = { path -> screenBackStackModel.mainScreen.navigateTo(NormalNavKey.LogView(path)) },
                        onShortcut = { id ->
                            val setting = when (id) {
                                "java" -> NormalNavKey.Settings.JavaManager
                                "renderer" -> NormalNavKey.Settings.Renderer
                                "game" -> NormalNavKey.Settings.Game
                                "control" -> NormalNavKey.Settings.Control
                                "gamepad" -> NormalNavKey.Settings.Gamepad
                                "layouts" -> NormalNavKey.Settings.ControlManager
                                "launcher" -> NormalNavKey.Settings.Launcher
                                "about" -> NormalNavKey.Settings.AboutInfo
                                else -> null
                            }
                            if (setting != null) {
                                screenBackStackModel.settingsScreen.clearWith(setting)
                                screenBackStackModel.mainScreen.removeAndNavigateTo(
                                    removes = screenBackStackModel.clearBeforeNavKeys,
                                    screenKey = screenBackStackModel.settingsScreen
                                )
                            } else when (id) {
                                "versions" -> screenBackStackModel.mainScreen.navigateTo(NormalNavKey.VersionsManager)
                                "mods" -> screenBackStackModel.navigateToDownload(screenBackStackModel.downloadModScreen)
                                "download" -> screenBackStackModel.navigateToDownload()
                                "multiplayer" -> screenBackStackModel.mainScreen.navigateTo(NormalNavKey.Multiplayer)
                                "account" -> screenBackStackModel.mainScreen.navigateTo(NormalNavKey.AccountManager())
                                "files" -> eventViewModel.sendEvent(EventViewModel.Event.OpenFileManager(rootPath = PathManager.DIR_FILES_EXTERNAL.absolutePath))
                                else -> Unit
                            }
                        }
                    )
                }
'''
    edit(main, '                entry<NormalNavKey.LauncherMain> {', entry + '                entry<NormalNavKey.LauncherMain> {')
    viewmodel = java / 'viewmodel/ScreenBackStackViewModel.kt'
    edit(viewmodel, 'NormalNavKey.Multiplayer::class', 'NormalNavKey.Multiplayer::class,\n        NormalNavKey.AuroraTools::class')
    settings_defaults = java / 'setting/AllSettings.kt'
    edit(settings_defaults, 'if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) ColorThemeType.DYNAMIC\n        else ColorThemeType.EMBERMIRE', 'ColorThemeType.CUSTOM // Aurora default; all original themes remain selectable.')
    edit(settings_defaults, 'Color.Blue.toArgb()', 'Color(0xFF09B9CA).toArgb()')
    activity = java / 'ui/activities/MainActivity.kt'
    edit(activity, 'launcherUpgradeViewModel.checkOnAppStart()', 'com.movtery.zalithlauncher.ui.screens.content.aurora.checkAuroraUpdate(this@MainActivity, lifecycleScope)')
    edit(activity, '                        checkUpdate()', '                        com.movtery.zalithlauncher.ui.screens.content.aurora.checkAuroraUpdate(this@MainActivity, lifecycleScope, force = true)')
    # Searchable sidebar for BOTH settings and downloads: original categories and nested routes retained.
    for name, selected, items in [('SettingsScreen.kt', 'settingsScreenKey', 'settingItems'), ('DownloadScreen.kt', 'downloadScreenKey', 'downloadItems')]:
        file = java / 'ui/screens/content' / name
        text = file.read_text()
        # The upstream download list has a different name: determine from the actual loop.
        a = text.index('@Composable\nprivate fun TabMenu(')
        b = text.index('\n@Composable', a+20)
        old = text[a:b]
        list_name = re.search(r'(\w+)\.forEach \{ item ->', old).group(1)
        # Download favorites counts and badges remain represented by the original page content.
        signature = old[:old.index(') {')+3]
        body = '''
    com.movtery.zalithlauncher.ui.screens.content.aurora.AuroraSettingsMenu(
        items = LIST,
        selected = SELECTED,
        navigate = navigateTo,
        modifier = modifier
    )
}
'''.replace('LIST', list_name).replace('SELECTED', selected)
        # Download TabMenu has extra account/favorites behavior; only settings is redesigned here.
        if name == 'SettingsScreen.kt':
            file.write_text(text[:a] + signature + body + text[b:])
        else:
            initial = old[:old.index('    val ctx = rememberAnimatedContext')]
            download_body = body.replace('selected = downloadScreenKey', 'selected = backScreenViewModel.downloadScreen.currentKey').replace('navigate = navigateTo', 'navigate = { backStack.navigateOnce(it) }').replace('modifier = modifier', 'modifier = modifier, title = "资源导航"')
            file.write_text(text[:a] + initial + download_body + text[b:])
    about = java / 'ui/screens/content/settings/AboutInfoScreen.kt'
    edit(about, '        ) {\n            animatedItem { ctx ->', '''        ) {
            animatedItem { ctx ->
                com.movtery.zalithlauncher.ui.screens.content.aurora.AuroraIdentityCard(
                    modifier = Modifier.animated(ctx), openLink = openLink
                )
            }
            animatedItem { ctx ->''')
    edit(about, 'title = stringResource(R.string.about_launcher_title)', 'title = "运行核心与开源来源"')
    edit(about, 'title = stringResource(R.string.about_launcher_author_movtery_title)', 'title = "上游核心作者 · MovTery"')
    edit(about, 'text = stringResource(R.string.about_launcher_author_movtery_text, launcherName)', 'text = "Zalith Launcher 2 原作者及贡献者。Aurora 保留其版权、许可与技术贡献记录。"')
    edit(about, 'title = BuildKeys.LAUNCHER_NAME,', 'title = "Zalith Launcher 2 / PojavLauncher",')
    edit(about, 'onClick = checkUpdate', 'onClick = { openLink("https://github.com/reunionSama/AuroraLauncher/releases") }')
    # Do not feed derivative users an incompatible upstream APK from the default update prompt.
    settings = java / 'ui/screens/content/SettingsScreen.kt'
    edit(settings, 'eventViewModel.sendEvent(EventViewModel.Event.CheckUpdate)', 'eventViewModel.sendEvent(EventViewModel.Event.OpenLink("https://github.com/reunionSama/AuroraLauncher/releases"))')
    res = module / 'src/main/res/values/aurora.xml'
    res.write_text('<resources><string name="aurora_tools">Aurora 工具</string></resources>')
    info = module / 'src/main/assets/AURORA_BUILD_INFO.json'
    metadata = json.loads(info.read_text())
    metadata['version'] = 'alpha3'
    metadata['aurora_additions'] = ['workspace', 'shortcut-favorites', 'instance-notes', 'preflight-checks', 'parallel-network-probes', 'bounded-live-log-tail', 'searchable-settings', 'aurora-default-palette', 'aurora-release-channel', 'maintainer-and-upstream-separation']
    info.write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    tests = module / 'src/test/java/com/movtery/zalithlauncher/ui/screens/content/aurora'
    tests.mkdir(parents=True, exist_ok=True)
    for test in (Path(__file__).parent / 'tests').glob('*.kt'):
        shutil.copy2(test, tests / test.name)
    print('Aurora original workspace, diagnostics, settings navigation and attribution applied.')

if __name__ == '__main__':
    import sys
    apply(sys.argv[1])

