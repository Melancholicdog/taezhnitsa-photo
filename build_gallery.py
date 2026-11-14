#!/usr/bin/env python3
"""Create small, non-cropped WebP photos and static catalog manifest."""
from pathlib import Path
import json
import re
import shutil
import unicodedata

from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
INPUT = ROOT / "photos"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif"}
TITLE_OVERRIDES = {
    "34f30801e1c85d91ec1e466737670f7c": "Дочь Байкала — тёмный шоколад",
    "hgcpl7ybcw": "Шоколад «Таёжница»",
    "image-photoroom (10)": "Шоколад «Вкус Байкала»",
}


def normalized(value):
    return unicodedata.normalize("NFC", value)


def clean_title(filename, brand):
    name = normalized(Path(filename).stem)
    name = re.sub(r"^\d{1,3}\s*[-.)]\s*", "", name).replace("_", " ").strip()
    low = name.lower()
    for key, title in TITLE_OVERRIDES.items():
        if low.startswith(key):
            return title
    if re.fullmatch(r"[a-f0-9]{24,}", low) or (
        len(name) > 38 and not re.search("[А-Яа-яЁё]", name)
    ):
        return "Шоколадная коллекция" if brand == "medoed" else "Продукция Таёжницы"
    return name or "Продукция"


def save_webp(original, dest, long_edge, quality):
    with Image.open(original) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((long_edge, long_edge), Image.Resampling.LANCZOS)
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "WEBP", quality=quality, method=5)
        return image.size


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    shutil.copy2(ROOT / "index.html", DIST / "index.html")
    (DIST / ".nojekyll").touch()

    entries = []
    for brand in ("taezhnitsa", "medoed"):
        folder = INPUT / brand
        if not folder.is_dir():
            continue
        files = sorted(
            (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS),
            key=lambda f: normalized(f.name).casefold(),
        )
        for i, photo in enumerate(files):
            uid = f"{brand}-{i + 1:03}"
            slug = re.sub(r"[^a-z0-9-]", "-", uid)
            base = f"media/{brand}/{slug}"
            small = DIST / f"{base}-preview.webp"
            large = DIST / f"{base}-large.webp"
            try:
                save_webp(photo, small, 860, 78)
                save_webp(photo, large, 2200, 87)
                thumb = small.relative_to(DIST).as_posix()
                full = large.relative_to(DIST).as_posix()
            except (UnidentifiedImageError, OSError, ValueError):
                # Keep the original file when the installed image library does not decode it.
                fallback = DIST / "media" / brand / (slug + photo.suffix.lower())
                fallback.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(photo, fallback)
                thumb = fallback.relative_to(DIST).as_posix()
                full = thumb
            entries.append({
                "id": normalized(brand + "-" + photo.name),
                "title": clean_title(photo.name, brand),
                "brand": brand,
                "src": thumb,
                "thumb": thumb,
                "full": full,
            })
    (DIST / "photos.js").write_text(
        "window.CATALOG_PHOTOS=" + json.dumps(entries, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"Published {len(entries)} photos, thumbnails and full-size versions")


if __name__ == "__main__":
    main()
