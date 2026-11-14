#!/usr/bin/env python3
from pathlib import Path
import json, shutil, re, unicodedata
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'dist'
SUFFIXES={'.jpg','.jpeg','.png','.webp','.gif','.avif'}
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
shutil.copy2(ROOT/'index.html',OUT/'index.html')
if (ROOT/'photos').is_dir():shutil.copytree(ROOT/'photos',OUT/'photos')
else:(OUT/'photos').mkdir()
items=[]
for brand in ('taezhnitsa','medoed'):
    d=OUT/'photos'/brand
    if not d.exists():continue
    for f in sorted(d.iterdir(),key=lambda x:x.name.casefold()):
        if not f.is_file() or f.suffix.lower() not in SUFFIXES:continue
        title=re.sub(r'^\d{1,3}\s*[-.]\s*','',f.stem.replace('_',' ')).strip()
        identifier=re.sub(r'[^\w-]+','-',unicodedata.normalize('NFKC',brand+'-'+f.name).lower()).strip('-')
        items.append({'id':identifier,'title':title,'brand':brand,'src':'photos/'+brand+'/'+f.name})
(OUT/'photos.js').write_text('window.CATALOG_PHOTOS='+json.dumps(items,ensure_ascii=False)+';\n',encoding='utf-8')
(OUT/'.nojekyll').touch()
print('Gallery photos:',len(items))
