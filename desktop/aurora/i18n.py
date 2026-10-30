# Copyright (C) 2026 reunionSama. SPDX-License-Identifier: GPL-3.0-or-later
"""Immediate, persisted UI language changes. User content and game logs stay original."""
import functools,json,re,sys
from pathlib import Path
LANGUAGES=('zh_CN','ja_JP','ko_KR','en_US')

@functools.lru_cache(maxsize=1)
def catalog():
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
    return json.loads((root/'assets/translations.json').read_text('utf-8'))

@functools.lru_cache(maxsize=3)
def replacer(language):
    values={key:item[language] for key,item in catalog().items() if language in item and re.search('[\u4e00-\u9fff]',key)}
    return re.compile('|'.join(re.escape(k) for k in sorted(values,key=len,reverse=True))),values

def translate(text,language):
    text=str(text)
    if language=='zh_CN' or language not in LANGUAGES:return text
    value=catalog().get(text,{}).get(language)
    if value is not None:return value
    pattern,values=replacer(language)
    return pattern.sub(lambda match:values[match[0]],text)
