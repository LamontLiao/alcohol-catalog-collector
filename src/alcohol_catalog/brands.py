from __future__ import annotations

import csv
from pathlib import Path

import yaml

from .normalize import brand_aliases, brand_key, clean_text, suspicious


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["categories"]


def parse_brand_files(inputs: Path, config_path: Path, output: Path) -> list[dict]:
    config = load_config(config_path)
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for path in sorted(inputs.glob("*.md")):
        category = path.stem
        if category not in config:
            continue
        for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            line = clean_text(raw)
            if not line or line.startswith("#"):
                continue
            primary, latin = brand_aliases(line)
            key = brand_key(primary, latin)
            if not key or (category, key) in seen:
                continue
            seen.add((category, key))
            reasons = suspicious(line)
            rows.append({
                "category_cn": category,
                "category_slug": config[category]["slug"],
                "raw_name": line,
                "brand": primary,
                "latin_alias": latin,
                "brand_key": key,
                "input_file": path.name,
                "input_line": number,
                "clean_status": "needs_review" if reasons else "candidate",
                "review_reason": "|".join(reasons),
                "verified_category": "",
                "verification_source": "",
            })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader(); writer.writerows(rows)
    return rows

