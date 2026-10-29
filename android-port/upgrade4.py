from pathlib import Path
import shutil,re,json

def apply(root):
 root=Path(root);m=root/'ZalithLauncher';j=m/'src/main/java/com/movtery/zalithlauncher';pet=root/'PetLib'
 def change(p,a,b):
  t=p.read_text();assert a in t,(p,a[:70]);p.write_text(t.replace(a,b))
 # Add distinct procedural skeleton poses; preserve original animation implementations.
 p=pet/'src/main/java/com/movtery/petlib/PetAnimation.kt'
 names=['Wave','Nod','LookAround','Bow','Cheer','Stretch','Sway','March','Run','Jump','Dance','Salute','Think','Clap','Balance','Lean','ShoulderRoll','LookUp','Kick','Celebrate']
 change(p,'    Walking(1),','    Walking(1),\n'+''.join(f'    Aurora{n}({i+2}),\n' for i,n in enumerate(names)))
 a=pet/'rust/src/animation.rs';change(a,'    Walking,','    Walking,\n    Aurora(u8),')
 with a.open('a') as f:f.write((Path(__file__).parent/'aurora_motion.rs').read_text())
 p=pet/'rust/src/jni.rs';change(p,'1 => Some(AnimationId::Walking),','1 => Some(AnimationId::Walking),\n        2..=21 => Some(AnimationId::Aurora((animation - 2) as u8)),') if False else None
 t=p.read_text();line=next(l for l in t.splitlines() if '1 => Some(AnimationId::Walking)' in l);before=t[:t.index(line)];var=re.search(r'match\s+(\w+)\s*\{\s*0 =>',t).group(1);change(p,line,line+f'\n        2..=21 => Some(AnimationId::Aurora(({var} - 2) as u8)),')
 p=pet/'rust/src/pose.rs';t=p.read_text().replace('    Walking,','    Walking,\n    Aurora(u8),').replace('Source::Idle | Source::Walking','Source::Idle | Source::Walking | Source::Aurora(_)')
 t=t.replace('AnimationId::Walking => Source::Walking,','AnimationId::Walking => Source::Walking,\n            AnimationId::Aurora(n) => Source::Aurora(n),')
 t=t.replace('            None => {}\n        }\n\n        // 权重', '''            Some((AnimationId::Aurora(n), speed, _)) => {
                if let Some(base) = self.tracks.iter_mut().find(|t| t.source == Source::Aurora(n)) {
                    base.time = (base.time + (dt * speed).min(0.05)) % 6.0;
                }
            }
            None => {}
        }

        // 权重''')
 t=t.replace('Source::Walking => snapshot_from_frame(evaluate_walking(track.time), cape_z),','Source::Walking => snapshot_from_frame(evaluate_walking(track.time), cape_z),\n            Source::Aurora(n) => snapshot_from_frame(crate::animation::evaluate_aurora(n, track.time), cape_z),');p.write_text(t)
 # Home opts into new actions; other previews retain existing behavior.
 p=j/'ui/components/_PetLib.kt';change(p,'    gazeEnabled: Boolean = true,','    gazeEnabled: Boolean = true,\n    auroraAuto: Boolean = false,')
 change(p,'    var previewBounds by remember', '''    val auroraPrefs = com.movtery.zalithlauncher.ui.screens.content.aurora.rememberAuroraPreferences()
    val auroraLifecycle = androidx.lifecycle.compose.LocalLifecycleOwner.current
    LaunchedEffect(petController, auroraAuto, auroraPrefs.actions, auroraPrefs.interval, auroraLifecycle) {
        if (auroraAuto && auroraPrefs.actions) {
            auroraLifecycle.lifecycle.repeatOnLifecycle(androidx.lifecycle.Lifecycle.State.RESUMED) {
                // Resume with a smooth idle pose; changing sky sliders does not reset actions.
                petController.playAnimation(PetAnimation.Idle)
                var last = -1
                kotlinx.coroutines.delay(auroraPrefs.interval * 1000L)
                while (true) {
                    var next = kotlin.random.Random.nextInt(20)
                    if (next == last) next = (next + 1) % 20
                    last = next
                    petController.playAnimation(PetAnimation.entries[next + 2], headFollow = false)
                    kotlinx.coroutines.delay(3200)
                    petController.playAnimation(PetAnimation.Idle)
                    kotlinx.coroutines.delay((auroraPrefs.interval * 1000L - 3200L).coerceAtLeast(500L))
                }
            }
        } else if (auroraAuto) petController.playAnimation(PetAnimation.Idle)
    }
    var previewBounds by remember''')
 # extension requires import, even when the receiver is qualified.
 change(p,'import androidx.compose', 'import androidx.compose') if False else None
 t=p.read_text();pos=t.index('\nimport ');t=t[:pos]+'\nimport androidx.lifecycle.repeatOnLifecycle\n'+t[pos:];p.write_text(t)
 p=j/'ui/screens/content/LauncherScreen.kt';change(p,'            dragYaw = false','            dragYaw = true,\n            auroraAuto = true')
 change(p,'        HomeGrid(\n','''        Box(modifier = modifier.fillMaxSize()) {
        com.movtery.zalithlauncher.ui.screens.content.aurora.AuroraSky(isVisible)
        HomeGrid(
''');change(p,'            modifier = modifier\n                .fillMaxSize()\n                .animated(ctx)\n        )','''            modifier = Modifier.fillMaxSize().animated(ctx)
        )
        com.movtery.zalithlauncher.ui.screens.content.aurora.AuroraHomeControls(Modifier.align(Alignment.BottomStart))
        }''')
 p=j/'ui/screens/content/home/HomeCards.kt';change(p,'            add(debugWarningCard())','            // Aurora home uses its own compact identity; build status remains in About.')
 # Retain required licenses and contributors in a dedicated expandable section; remove sponsor marketing.
 p=j/'ui/screens/content/settings/AboutInfoScreen.kt';t=p.read_text();start=t.index('            animatedItem { ctx ->',t.index('AuroraIdentityCard'))
 end=t.index('            //已加载插件板块',start)
 original=t[start:end]
 asset=m/'src/main/assets/AURORA_UPSTREAM_CREDITS.txt';asset.write_text('Zalith Launcher 2 — MovTery and contributors; PojavLauncher and contributors.\nGPL-3.0-or-later; all original source headers, component licenses and credits retained.\nSources: https://github.com/ZalithLauncher/ZalithLauncher2\nhttps://github.com/PojavLauncherTeam/PojavLauncher\n\nOriginal credit screen implementation follows as an archival attribution record:\n'+original)
 # Keep full credit implementation reachable, but without a wall of donor/project logos on the main About page.
 t=t[:start]+'''            animatedItem { ctx ->
                com.movtery.zalithlauncher.ui.screens.content.aurora.AuroraLegalCard(
                    openLicense = openLicense, openLink = openLink
                )
            }
'''+t[end:];p.write_text(t)
 # Replace all user-facing project URLs in Aurora additions; do not rewrite third-party source references.
 for p in (j/'ui/screens/content/aurora').glob('*.kt'):
  s=p.read_text().replace('https://github.com/reunionSama/AuroraLauncher"','https://github.com/reunionSama/AuroraLauncher-Android"').replace('https://github.com/reunionSama/AuroraLauncher/releases','https://github.com/reunionSama/AuroraLauncher-Android/releases');p.write_text(s)
 p=j/'ui/screens/content/SettingsScreen.kt';change(p,'eventViewModel.sendEvent(EventViewModel.Event.OpenLink("https://github.com/reunionSama/AuroraLauncher/releases"))','eventViewModel.sendEvent(EventViewModel.Event.CheckUpdate)')
 p=j/'ui/activities/MainActivity.kt';change(p,'                    is EventViewModel.Event.Launch.Game -> {','''                    is EventViewModel.Event.Launch.Game -> {
                        com.movtery.zalithlauncher.ui.screens.content.aurora.checkAuroraUpdate(this@MainActivity, lifecycleScope)''')
 for case in ['PlayServer','PlaySave']:
  change(p,'                    is EventViewModel.Event.Launch.'+case+' -> {','                    is EventViewModel.Event.Launch.'+case+' -> {\n                        com.movtery.zalithlauncher.ui.screens.content.aurora.checkAuroraUpdate(this@MainActivity, lifecycleScope)')
 manifest=m/'src/main/AndroidManifest.xml';change(manifest,'    <application','    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />\n    <application')
 for p in (j/'ui/screens/content/aurora').glob('*.kt'):
  if p.name=='AuroraIdentityCard.kt':
   s=p.read_text().replace('AuroraLauncher 安卓','AuroraLauncher 安卓').replace('"Aurora 更新"','"发布记录"');p.write_text(s)
 (m/'src/main/assets/AURORA_CHANNEL.json').write_text(json.dumps({'repo':'reunionSama/AuroraLauncher-Android','version_code':200050,'motion_count':20,'interval_seconds':15,'build_time':__import__('time').time_ns()//1000000}))
 info=m/'src/main/assets/AURORA_BUILD_INFO.json'
 meta=json.loads(info.read_text());meta['version']='alpha5';meta['aurora_additions']+=['aurora-sky','twenty-skeleton-gestures','in-app-downloader'];info.write_text(json.dumps(meta,ensure_ascii=False,indent=2))
 print('Applied Aurora Alpha4 motion, sky, personalization and native update integration.')

