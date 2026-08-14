from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def leaf_paths(topic: dict, parents: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    current = parents + (str(topic["title"]),)
    children = topic.get("children", {}).get("attached", [])
    if not children:
        return [current]
    return [path for child in children for path in leaf_paths(child, current)]


def read_xmind_leaf_paths(path: Path) -> set[tuple[str, ...]]:
    with zipfile.ZipFile(path) as archive:
        sheets = json.loads(archive.read("content.json"))
    return {
        leaf
        for sheet in sheets
        for leaf in leaf_paths(sheet["rootTopic"])
    }


def read_taxonomy_paths(path: Path) -> set[tuple[str, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {tuple(item["path"]) for item in payload["categories"]}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that the semantic taxonomy covers every XMind leaf"
    )
    parser.add_argument("xmind", type=Path)
    parser.add_argument(
        "--taxonomy",
        type=Path,
        default=Path("configs/industry_taxonomy.json"),
    )
    parser.add_argument(
        "--exact",
        action="store_true",
        help="Also fail when the semantic taxonomy intentionally extends the XMind leaves",
    )
    args = parser.parse_args()

    xmind_paths = read_xmind_leaf_paths(args.xmind)
    taxonomy_paths = read_taxonomy_paths(args.taxonomy)
    missing = sorted(xmind_paths - taxonomy_paths)
    extra = sorted(taxonomy_paths - xmind_paths)
    print(f"XMind leaf paths: {len(xmind_paths)}")
    print(f"Taxonomy paths: {len(taxonomy_paths)}")
    for path in missing:
        print(f"MISSING: {' > '.join(path)}")
    for path in extra:
        print(f"EXTRA: {' > '.join(path)}")
    return 1 if missing or (args.exact and extra) else 0


if __name__ == "__main__":
    raise SystemExit(main())
