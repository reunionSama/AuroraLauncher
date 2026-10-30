# AuroraLauncher Desktop 6

A new Windows desktop implementation of AuroraLauncher's Android interaction model.
Maintainer: reunionSama. Application version: 6.1.0 (build 61000). Windows 10/11 x64.

This project replaces the previous desktop implementation. It does not wrap an APK,
run an Android emulator, or reuse the previous Python desktop launcher UI/source.

The Qt Quick UI ports the aurora home, rotatable textured player, twenty smooth
skeletal gestures, personalization, creator sponsorship, accounts, versions,
resource management and tools. Minecraft runs using the native Windows Java client.
Android-specific renderers and touch controls are replaced with desktop rendering,
keyboard/mouse controls and per-game Java runtime selection.

## Version 6.1.0

- Account preview now includes the active official Minecraft cape, with an
  animated back-mounted mesh and cached account texture. No cape is invented
  for an account without an active cape. Existing drag/click/twenty actions stay.
- The instructional sentence below the player is removed; interaction stays.
- A version-specific component installer lists Fabric, Forge, NeoForge, Quilt,
  OptiFine, Fabric API and Quilted Fabric API. Exact versions are selected;
  incompatible primary loaders and mismatched APIs are rejected. OptiFine uses
  its separately downloaded official installer; no OptiFine jar is bundled.
- Live logs support Ctrl+F, case matching, previous/next occurrence, count,
  selection and matching-line filtering while retaining the original export.
- A small source-built Java agent adds AuroraLauncher(version) to the title
  screen version text and F3 client brand. Official Mojang class mappings find
  obfuscated classes. Game jars on disk are unchanged; existing loader branding
  is retained. A setting can disable the cosmetic component.
- Chinese, Japanese, Korean and English switch instantly and persist, with a
  complete interface catalog. User content, version IDs and game logs are not
  translated. Windows file dialogs follow the operating system language.

## Features

- Original Aurora star icon; selected Microsoft account skin, slim/classic model
  and second skin layer; offline cache, custom PNG override and restore-account
  button. Eased drag rotation, twenty gestures and feathered Aurora 60/30 FPS modes.
- Page fades, reduced-motion setting, full button labels, compact 960x620 layout
  and remembered window size; native Windows resize, minimize and maximize.
- Vanilla, Fabric, Quilt, Forge and NeoForge installations; official/BMCLAPI source
  preference, bounded retries, parallel downloads, resume and hash verification.
- Microsoft device-code login, local offline profiles and multiple accounts.
  Public client ID: `785d7402-026c-44d0-ae65-d4b29eb27d3c`. Windows account tokens
  are encrypted using DPAPI. No client secret is embedded.
- Per-instance mods, packs, shaders, saves and notes; Modrinth search, compatible
  releases and required dependencies; `.mrpack` import and isolated pack instances.
- Native game process launch, bounded real-time redacted logs, crash hints and
  log export. Game files and Java are obtained when requested, not bundled.
- World backups/restoration into new folders; Aurora instance import/export;
  source and network diagnostics and Java detection/automatic runtime installation.
- Official unmodified Terracotta 0.4.2 x64 process and documented local HTTP API:
  host/join/reset, invitation code, members and direct-connect address.
- Windows updates use the fixed `publicLauncher` release in this repository.
  Conditional API requests, rate-limit cooldown, parallel release-page fallback
  and recent/offline caches avoid repeated 403 failures. The updater checks the
  EXE timestamp and declared version to avoid offering the old desktop build.
  Downloads stay in-app and require the GitHub SHA256. Update notes come from
  the same GitHub release. For new uploads, update the version in the release
  description (e.g. V6.0.2), replace AuroraLauncher.exe and retain its SHA256.
- Microsoft login opens the verification URI returned with the device code
  (currently https://www.microsoft.com/link), with a safe microsoft.com/link fallback.

## Build and testing

Run `desktop/BUILD_WINDOWS.bat` with Python 3.12. Install a JDK 17+ for the source-built branding component. Build dependencies use the Aliyun
PyPI index. The result is one `desktop/dist/AuroraLauncher.exe`; Python is embedded.
The build generates original deterministic assets and retrieves an unmodified,
SHA256-pinned OFL font. The corresponding modified source and licenses accompany
successful CI builds.

`.github/workflows/windows-rebuild.yml` builds on Windows, runs unit tests, launches
both source and the actual packaged executable, visits all eleven UI pages, checks
real mouse-drag rotation, cape preview, log search, installer UI, four languages,
compact layout and the sponsor entry, and attempts a real Minecraft 1.20.1
demo-mode window through the packaged executable. CI's software OpenGL is confined
to the ephemeral test machine and is not distributed as part of Aurora. Official
loader installations and selected Fabric API are tested in separate CI instances.

Successful UI tests do not substitute for user-account login or multiplayer tests.
No Microsoft password or real user credentials are used by automated tests.

## License and provenance

GPL-3.0-or-later. Aurora Android's gesture equations are retained with attribution.
Zalith Launcher 2: MovTery and contributors; PojavLauncher: its credited contributors.
Qt/PySide6, minecraft-launcher-lib, Terracotta, Noto and other components preserve
separate license terms. See `desktop/assets/THIRD_PARTY_NOTICES.txt` and LICENSE.
AzureLauncher (D3sp1r4t) has no license; no code or art from it is redistributed.

Data defaults to `%LOCALAPPDATA%/AuroraLauncher/Desktop6`. Previous desktop data is
not deleted. An existing `.minecraft` library can be selected through settings.

