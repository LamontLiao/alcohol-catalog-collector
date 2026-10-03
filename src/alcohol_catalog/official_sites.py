from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .brands import load_config
from .normalize import brand_key, clean_text


BING_RSS = "https://www.bing.com/search"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
BLOCKED_DOMAINS = {
    "amazon", "alibaba", "aliexpress", "ebay", "jd", "taobao", "tmall", "walmart",
    "carrefour", "vivino", "wine-searcher", "wine-searcher", "masterofmalt", "totalwine",
    "drizly", "whiskybase", "whiskyauctioneer", "wikipedia", "wikidata", "facebook",
    "instagram", "youtube", "tiktok", "linkedin", "reddit", "pinterest", "x",
}
ALCOHOL_TERMS = {
    "whisky": ("whisky", "whiskey", "bourbon", "scotch", "distillery"),
    "sake": ("sake", "nihonshu", "sake brewery", "sake producer"),
    "tequila": ("tequila", "mezcal", "agave", "distillery"),
    "gin": ("gin", "genever", "distillery"),
    "rum": ("rum", "rhum", "ron", "distillery"),
    "liqueur": ("liqueur", "amaro", "aperitif", "liqueur brand"),
    "vodka": ("vodka", "distillery", "spirits brand"),
    "brandy": ("brandy", "cognac", "armagnac", "pisco", "distillery"),
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff]", "", value)


def query_for(row: dict, category_name: str) -> str:
    names = [clean_text(row.get("brand", "")), clean_text(row.get("latin_alias", ""))]
    names = [x for x in dict.fromkeys(names) if x]
    return " ".join(names + [category_name, "brand official website"])


def _cache_path(cache: Path, key: str) -> Path:
    return cache / (hashlib.sha256(key.encode("utf-8")).hexdigest() + ".txt")


class WebLookup:
    def __init__(self, cache: Path, delay: float = 0.8):
        self.cache = cache
        self.cache.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.last: dict[str, float] = {}

    def _get(self, url: str, params: dict[str, str]) -> bytes:
        key = url + "?" + urlencode(params)
        path = _cache_path(self.cache, key)
        if path.exists():
            return path.read_bytes()
        host = urlparse(url).netloc
        elapsed = time.monotonic() - self.last.get(host, 0.0)
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        target = key
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                request = Request(target, headers={
                    "User-Agent": "AlcoholCatalogResearch/0.2 (public brand website lookup)",
                    "Accept": "application/rss+xml, application/xml, application/json;q=0.9, */*;q=0.5",
                })
                with urlopen(request, timeout=35) as response:
                    payload = response.read(2_000_001)
                    if len(payload) > 2_000_000:
                        raise ValueError("response_too_large")
                path.write_bytes(payload)
                self.last[host] = time.monotonic()
                return payload
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    time.sleep(min(16, 2 ** attempt))
        raise RuntimeError(type(last_error).__name__ if last_error else "request_failed")

    def bing(self, query: str) -> list[dict]:
        payload = self._get(BING_RSS, {"q": query, "format": "rss", "setlang": "en-US"})
        root = ET.fromstring(payload)
        results: list[dict] = []
        for item in root.findall(".//item")[:10]:
            title = clean_text(item.findtext("title") or "")
            link = clean_text(item.findtext("link") or "")
            description = clean_text(item.findtext("description") or "")
            if not link.startswith("http"):
                continue
            results.append({"title": title, "url": link, "description": description})
        return results

    def wikidata_official(self, row: dict, category_slug: str) -> dict | None:
        terms = [clean_text(row.get("brand", "")), clean_text(row.get("latin_alias", ""))]
        terms = [x for x in dict.fromkeys(terms) if x]
        category_terms = ALCOHOL_TERMS.get(category_slug, ())
        for term in terms:
            data = json.loads(self._get(WIKIDATA_API, {
                "action": "wbsearchentities", "search": term, "language": "en", "uselang": "en",
                "type": "item", "limit": "6", "format": "json",
            }).decode("utf-8"))
            for hit in data.get("search", []):
                label = clean_text(hit.get("label", ""))
                description = clean_text(hit.get("description", ""))
                if norm(label) != norm(term):
                    continue
                if category_terms and not any(t in description.casefold() for t in category_terms):
                    continue
                entity = json.loads(self._get(WIKIDATA_API, {
                    "action": "wbgetentities", "ids": hit["id"], "props": "claims|labels|descriptions",
                    "languages": "en", "format": "json",
                }).decode("utf-8"))
                claims = entity.get("entities", {}).get(hit["id"], {}).get("claims", {})
                urls = []
                for claim in claims.get("P856", []):
                    value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                    if isinstance(value, str) and value.startswith("http"):
                        urls.append(value)
                if urls:
                    return {"url": urls[0], "entity": hit.get("concepturi", ""), "label": label, "description": description}
        return None


def _domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def is_excluded(url: str) -> bool:
    host = _domain(url)
    parts = set(host.split("."))
    return any(block in parts or host.endswith("." + block + ".com") or host == block + ".com" for block in BLOCKED_DOMAINS)


def classify_results(results: list[dict], row: dict) -> tuple[str, list[dict], str]:
    names = [clean_text(row.get("brand", "")), clean_text(row.get("latin_alias", ""))]
    terms = [norm(n) for n in names if len(norm(n)) >= 3]
    candidates: list[dict] = []
    for item in results:
        url = item["url"]
        if is_excluded(url):
            continue
        domain = norm(_domain(url).split(":")[0])
        text = norm(item.get("title", "") + " " + item.get("description", ""))
        if not terms:
            continue
        matched_name = [name for name, term in zip(names, [norm(n) for n in names]) if term and (term in domain or term in text)]
        if not matched_name:
            continue
        exact_domain = any(term in domain for term in terms)
        official_word = "official" in (item.get("title", "") + " " + item.get("description", "")).casefold()
        candidates.append({**item, "matched_name": matched_name[0], "domain_matches_brand": exact_domain, "mentions_official": official_word})
    candidates.sort(key=lambda item: (not item["domain_matches_brand"], not item["mentions_official"]))
    if not candidates:
        return "no_official_site_found", [], "搜索结果未出现可与品牌名关联的非电商、非社交网站；不代表品牌一定没有官网"
    best = candidates[0]
    if best["domain_matches_brand"]:
        return "likely_official_domain", candidates, "搜索结果域名包含品牌名称，仍需人工核验网站运营方"
    if best["mentions_official"]:
        return "possible_official_site", candidates, "搜索摘要提及官方页面，但域名未能与品牌名直接匹配"
    if len(candidates) > 1:
        return "ambiguous_candidates", candidates, "找到多个品牌相关站点，无法仅凭搜索结果确认运营主体"
    return "possible_official_site", candidates, "找到品牌相关站点，搜索结果不足以确认运营主体"


def check_brand(lookup: WebLookup, row: dict, category_name: str, category_slug: str) -> dict:
    query = query_for(row, category_name)
    result = {
        "category_cn": category_name,
        "category_slug": category_slug,
        "raw_name": row.get("raw_name", ""),
        "brand": row.get("brand", ""),
        "latin_alias": row.get("latin_alias", ""),
        "brand_key": row.get("brand_key", ""),
        "input_file": row.get("input_file", ""),
        "input_line": row.get("input_line", ""),
        "review_reason": row.get("review_reason", ""),
        "search_query": query,
        "official_status": "search_error",
        "official_website_url": "",
        "evidence_source": "",
        "evidence_detail": "",
        "candidate_sites_json": "[]",
    }
    try:
        results = lookup.bing(query)
        status, candidates, detail = classify_results(results, row)
        result["official_status"] = status
        result["evidence_source"] = "Bing RSS search"
        result["evidence_detail"] = detail
        if candidates:
            result["official_website_url"] = candidates[0]["url"]
            result["candidate_sites_json"] = json.dumps(candidates[:5], ensure_ascii=False)
        if status != "likely_official_domain":
            wikidata = lookup.wikidata_official(row, category_slug)
            if wikidata:
                result["official_status"] = "official_listed_on_wikidata"
                result["official_website_url"] = wikidata["url"]
                result["evidence_source"] = "Wikidata P856"
                result["evidence_detail"] = f"Wikidata exact-label entity: {wikidata['label']} — {wikidata['description']} ({wikidata['entity']})"
    except Exception as exc:
        result["evidence_detail"] = f"lookup_error:{type(exc).__name__}"
    return result


def run(category_slug: str, brands_csv: Path, config_path: Path, output_dir: Path, cache_dir: Path | None = None) -> Path:
    configs = load_config(config_path)
    category_name, config = next((name, value) for name, value in configs.items() if value["slug"] == category_slug)
    with brands_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.DictReader(f) if row["category_slug"] == category_slug]
    lookup = WebLookup(cache_dir or output_dir / "website_search_cache")
    results = [check_brand(lookup, row, category_name, category_slug) for row in rows]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"brand_official_sites_{category_slug}.csv"
    fields = list(results[0]) if results else ["category_cn", "category_slug", "raw_name", "brand", "latin_alias", "brand_key", "input_file", "input_line", "review_reason", "search_query", "official_status", "official_website_url", "evidence_source", "evidence_detail", "candidate_sites_json"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(results)
    counts: dict[str, int] = {}
    for item in results:
        counts[item["official_status"]] = counts.get(item["official_status"], 0) + 1
    print(json.dumps({"category": category_slug, "checked": len(results), "status_counts": counts, "output": str(path)}, ensure_ascii=False))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Search each listed brand for its official website")
    parser.add_argument("--category", required=True)
    parser.add_argument("--brands", type=Path, default=Path("output/brands_cleaning.csv"))
    parser.add_argument("--config", type=Path, default=Path("config/categories.yml"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    run(args.category, args.brands, args.config, args.output_dir)


if __name__ == "__main__":
    main()

