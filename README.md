# AuroraLauncher Desktop 6

A new Windows desktop implementation of AuroraLauncher's Android interaction model.
Maintainer: reunionSama. Application version: 6.0.0 (build 60001). Windows 10/11 x64.

This project replaces the previous desktop implementation. It does not wrap an APK,
run an Android emulator, or reuse the previous Python desktop launcher UI/source.

The Qt Quick UI ports the aurora home, rotatable textured player, twenty smooth
skeletal gestures, personalization, creator sponsorship, accounts, versions,
resource management and tools. Minecraft runs using the native Windows Java client.
Android-specific renderers and touch controls are replaced with desktop rendering,
keyboard/mouse controls and per-game Java runtime selection.

## Features

- Original Aurora star icon and explorer skin; user PNG skins; drag rotation and
  twenty gestures, every 15 seconds by default. Aurora 60/30 FPS modes.
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
- Windows updates read only `desktop-vX.Y.Z` GitHub releases from this repository,
  accept only the `AuroraLauncher.exe` asset with its GitHub SHA256, and download
  in-app. APK/old Windows releases are never treated as desktop updates.

## Build and testing

Run `desktop/BUILD_WINDOWS.bat` with Python 3.12. Build dependencies use the Aliyun
PyPI index. The result is one `desktop/dist/AuroraLauncher.exe`; Python is embedded.
The build generates original deterministic assets and retrieves an unmodified,
SHA256-pinned OFL font. The corresponding modified source and licenses accompany
successful CI builds.

`.github/workflows/windows-rebuild.yml` builds on Windows, runs unit tests, launches
both source and the actual packaged executable, visits all eleven UI pages, checks
real mouse-drag rotation and the sponsor entry, and attempts a real Minecraft 1.20.1
demo-mode window through the packaged executable. CI's software OpenGL is confined
to the ephemeral test machine and is not distributed as part of Aurora.

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
