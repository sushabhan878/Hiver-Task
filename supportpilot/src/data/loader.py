"""Loaders for raw and processed data files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pyarrow.parquet as pq


def load_raw_conversations(path: str | Path, brand: str | None = None,
                           columns: list[str] | None = None) -> list[dict]:
    """Stream the TNE-AI conversation parquet; optionally filter to one brand."""
    f = pq.ParquetFile(path)
    cols = columns or ["conversation_id", "company", "conversation"]
    rows = []
    for rg in range(f.num_row_groups):
        t = f.read_row_group(rg, columns=cols).to_pylist()
        for r in t:
            if brand is not None and r.get("company") != brand:
                continue
            rows.append(r)
    return rows


def write_jsonl(path: str | Path, rows: list[dict] | Iterable) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def read_json(path: str | Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
