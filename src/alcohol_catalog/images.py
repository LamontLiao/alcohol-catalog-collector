from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image


def download_image(url: str, directory: Path, stem: str) -> tuple[str, str]:
    if not url: return "", "missing_url"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        request = Request(url, headers={"User-Agent":"AlcoholCatalogResearch/0.1", "Accept":"image/*"})
        with urlopen(request, timeout=45) as response:
            ctype = response.headers.get("content-type", "").split(";")[0]
            if not ctype.startswith("image/"): return "", "not_image"
            data = response.read(20_000_001)
        if len(data) > 20_000_000: return "", "too_large"
        digest = hashlib.sha256(data).hexdigest()
        ext = mimetypes.guess_extension(ctype) or Path(urlparse(url).path).suffix or ".jpg"
        ext = ".jpg" if ext == ".jpe" else ext
        target = directory / f"{stem}_{digest[:12]}{ext}"
        if not target.exists(): target.write_bytes(data)
        with Image.open(target) as image: image.verify()
        return target.name, digest
    except Exception as exc:
        return "", f"download_error:{type(exc).__name__}"
