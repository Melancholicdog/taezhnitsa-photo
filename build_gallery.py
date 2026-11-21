#!/usr/bin/env python3
"""Build fast photo gallery with no cropped images or repeated identical photos."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import unicodedata
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT=Path(__file__).resolve().parent
DIST=ROOT/"dist"
INPUT=ROOT/"photos"
ALLOWED={".jpg",".jpeg",".png",".webp",".avif",".gif"}
TITLE_OVERRIDES={
    "34f30801e1c85d91ec1e466737670f7c": "Дочь Байкала — тёмный шоколад",
    "hgcpl7ybcw": "Шоколад «Таёжница»",
    "image-photoroom (10)": "Шоколад «Вкус Байкала»",
}

def normalized(text):
    return unicodedata.normalize("NFC", text)

def title_for(filename,brand):
    name=normalized(Path(filename).stem)
    name=re.sub(r"^\d{1,3}\s*[-.)]\s*","",name).replace("_"," ").strip()
    lower=name.lower()
    for prefix, title in TITLE_OVERRIDES.items():
        if lower.startswith(prefix):
            return title
    if re.fullmatch(r"[a-f0-9]{24,}",lower) or (len(name)>38 and not re.search("[А-Яа-яЁё]",name)):
        return "Шоколадная коллекция" if brand=="medoed" else "Продукция Таёжницы"
    return name or "Продукция"

def webp(source,destination,max_side,quality):
    with Image.open(source) as im:
        image=ImageOps.exif_transpose(im)
        image.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
        if image.mode not in {"RGB","RGBA"}:
            image=image.convert("RGBA" if ("A" in image.getbands() or "transparency" in image.info) else "RGB")
        destination.parent.mkdir(parents=True,exist_ok=True)
        image.save(destination,"WEBP",quality=quality,method=5)

def main():
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copy2(ROOT/"index.html",DIST/"index.html")
    (DIST/".nojekyll").touch()
    assets=ROOT/"assets"
    if assets.is_dir():
        shutil.copytree(assets,DIST/"assets")
    result=[]
    banner=None
    for brand in ("taezhnitsa","medoed"):
        folder=INPUT/brand
        if not folder.is_dir():continue
        seen=set()
        for photo in sorted(folder.iterdir(),key=lambda f:normalized(f.name).casefold()):
            if not photo.is_file() or photo.suffix.lower() not in ALLOWED:continue
            # This landscape promotional image does not fit the product-card gallery.
            # Preserve both Unicode variants of the source file in GitHub.
            if brand=="taezhnitsa" and normalized(photo.stem).casefold()=="сибирский кочевник среди снежных вершин":
                print("Excluded landscape promo from gallery:",photo.name)
                continue
            fingerprint=hashlib.sha256(photo.read_bytes()).hexdigest()
            if fingerprint in seen:
                print("Skipped duplicate",photo.name)
                continue
            seen.add(fingerprint)
            if brand=="taezhnitsa" and "жир" in normalized(photo.stem).casefold():
                banner=photo
                continue
            sequence=1+sum(1 for x in result if x["brand"]==brand)
            base=f"media/{brand}/{brand}-{sequence:03d}"
            preview=DIST/(base+"-preview.webp")
            large=DIST/(base+"-large.webp")
            try:
                webp(photo,preview,900,78)
                webp(photo,large,2200,88)
                small_path=preview.relative_to(DIST).as_posix()
                large_path=large.relative_to(DIST).as_posix()
            except (UnidentifiedImageError,OSError,ValueError):
                fallback=DIST/(base+photo.suffix.lower())
                fallback.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(photo,fallback)
                small_path=large_path=fallback.relative_to(DIST).as_posix()
            result.append({
                "id":normalized(brand+"-"+photo.name),
                "title":title_for(photo.name,brand),
                "brand":brand,
                "src":small_path,
                "thumb":small_path,
                "full":large_path,
            })
    if banner is not None:
        webp(banner,DIST/"featured"/"fats.webp",2400,85)
    (DIST/"photos.js").write_text(
        "window.CATALOG_PHOTOS="+json.dumps(result,ensure_ascii=False)+";\n",
        encoding="utf-8"
    )
    print("Built",len(result),"unique photos","fats banner",bool(banner))

if __name__=="__main__":
    main()
