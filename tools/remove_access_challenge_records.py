from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.content_quality import assess_content


def is_access_challenge(content: object) -> bool:
    _, issue = assess_content(
        str(content or ""),
        extraction_method="dom_or_structured_full_text",
    )
    return issue == "access_challenge"


def clean_jsonl(path: Path) -> int:
    kept: list[str] = []
    removed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if isinstance(record, dict) and is_access_challenge(record.get("content")):
            removed += 1
            continue
        kept.append(line)
    if removed:
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed


def clean_csv(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames or "content" not in fieldnames:
            return 0
        rows = list(reader)
    kept = [row for row in rows if not is_access_challenge(row.get("content"))]
    removed = len(rows) - len(kept)
    if removed:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(kept)
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove HTTP-200 access challenge pages accidentally stored as articles"
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()

    totals: dict[str, int] = {}
    jsonl_path = args.data_dir / "articles.jsonl"
    if jsonl_path.exists():
        totals[str(jsonl_path)] = clean_jsonl(jsonl_path)
    for csv_path in sorted(args.data_dir.rglob("articles*.csv")):
        totals[str(csv_path)] = clean_csv(csv_path)
    for path, count in totals.items():
        if count:
            print(f"{path}: removed {count} access challenge record(s)")
    print(f"total removed: {sum(totals.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
