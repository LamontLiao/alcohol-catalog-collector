from __future__ import annotations

import argparse
from pathlib import Path

from .brands import parse_brand_files


ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    clean = sub.add_parser("clean-brands")
    clean.add_argument("--inputs", type=Path, default=ROOT / "inputs")
    clean.add_argument("--config", type=Path, default=ROOT / "config/categories.yml")
    clean.add_argument("--output", type=Path, default=ROOT / "output/brands_cleaning.csv")
    run = sub.add_parser("collect")
    run.add_argument("--category", required=True)
    run.add_argument("--brands", type=Path, default=ROOT / "output/brands_cleaning.csv")
    run.add_argument("--config", type=Path, default=ROOT / "config/categories.yml")
    run.add_argument("--output-dir", type=Path, default=ROOT / "output")
    run.add_argument("--pages", type=int, default=8)
    sites = sub.add_parser("official-sites")
    sites.add_argument("--category", required=True)
    sites.add_argument("--brands", type=Path, default=ROOT / "output/brands_cleaning.csv")
    sites.add_argument("--config", type=Path, default=ROOT / "config/categories.yml")
    sites.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    if args.command == "clean-brands":
        rows = parse_brand_files(args.inputs, args.config, args.output); print(f"wrote {len(rows)} brand candidates to {args.output}")
    else:
        if args.command == "collect":
            from .pipeline import collect
            out = collect(args.category, args.brands, args.config, args.output_dir, args.pages)
        else:
            from .official_sites import run
            out = run(args.category, args.brands, args.config, args.output_dir)
        print(out)


if __name__ == "__main__": main()
