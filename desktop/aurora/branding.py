# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
import re,sys
from pathlib import Path
from . import VERSION

def agent_path():return Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))/'assets/AuroraBranding.jar'

def mapped_classes(text):
    title=['net/minecraft/client/gui/screens/TitleScreen','net/minecraft/client/gui/GuiMainMenu'];brand=['net/minecraft/client/ClientBrandRetriever']
    for line in text.splitlines():
        match=re.fullmatch(r'(net\.minecraft\.client\.(?:gui\.screens\.TitleScreen|gui\.GuiMainMenu|ClientBrandRetriever)) -> ([\w.$]+):',line)
        if match:(brand if match[1].endswith('ClientBrandRetriever') else title).append(match[2].replace('.','/'))
    return title,brand

def branding_args(engine,version):
    if not engine.store.settings.get('gameBranding',True):return []
    jar=agent_path()
    if not jar.is_file():raise RuntimeError('游戏标识组件缺失，请使用完整的 AuroraLauncher 安装包')
    path=engine.root/'assets/mappings'/(engine.base_version(version)+'.txt')
    title,brand=mapped_classes(path.read_text('utf-8') if path.is_file() else '')
    return ['-javaagent:'+str(jar)+'='+VERSION,'-Daurora.titleClasses='+','.join(title),'-Daurora.brandClasses='+','.join(brand)]
