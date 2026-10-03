from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class CachedClient:
    def __init__(self, cache: Path, delay: float = 1.0):
        self.cache = cache; self.cache.mkdir(parents=True, exist_ok=True)
        self.delay = delay; self.last: dict[str, float] = {}
        self.user_agent = "AlcoholCatalogResearch/0.1 (public-data research; GitHub Actions)"

    def _path(self, key: str) -> Path:
        import hashlib
        return self.cache / f"{hashlib.sha256(key.encode()).hexdigest()}.json"

    def json(self, url: str, params: dict | None = None) -> dict:
        key = url + "?" + json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
        path = self._path(key)
        if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
        host = urlparse(url).netloc
        elapsed = time.monotonic() - self.last.get(host, 0)
        if elapsed < self.delay: time.sleep(self.delay - elapsed)
        target = url + ("?" + urlencode(params) if params else "")
        for attempt in range(4):
            try:
                request = Request(target, headers={"User-Agent": self.user_agent, "Accept":"application/json"})
                with urlopen(request, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                break
            except Exception:
                if attempt == 3: raise
                time.sleep(min(20, 2 ** attempt))
        self.last[host] = time.monotonic()
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
