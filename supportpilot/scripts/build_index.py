"""Phase 3: build the retrieval index + intent example bank artifacts.

Loads labelled retrieval cases, embeds them, and persists:
- cache/index/cases_with_embeddings.npz (matrix + ids)
- cache/index/example_bank.jsonl (for the intent classifier)

Usage: python -m scripts.build_index
"""

from __future__ import annotations

import numpy as np

from scripts._bootstrap import ROOT  # noqa: F401
from src.config import project_path
from src.data.loader import read_jsonl, write_json, write_jsonl
from src.llm.client import get_client


def main():
    cases_path = project_path("data/processed/retrieval_cases_labelled.jsonl")
    cases = read_jsonl(cases_path)
    print(f"Loaded {len(cases):,} labelled retrieval cases")

    client = get_client()
    index_dir = project_path("cache/index")
    index_dir.mkdir(parents=True, exist_ok=True)
    npz_path = index_dir / "cases_with_embeddings.npz"

    case_ids = [c["case_id"] for c in cases]
    matrix = None
    if npz_path.exists():
        try:
            cached = np.load(npz_path, allow_pickle=False)
            if [str(x) for x in cached["case_ids"]] == case_ids:
                matrix = cached["matrix"].astype(np.float32)
                print(f"Reusing committed embedding matrix {matrix.shape}")
        except Exception:
            matrix = None
    if matrix is None:
        print(f"Embedding {len(cases):,} customer-problem texts with {client.embed_model}...")
        texts = [c["customer_problem"] for c in cases]
        embs = client.embed(texts)
        matrix = np.array(embs, dtype=np.float32)
        print(f"Embeddings: {matrix.shape}")

    np.savez_compressed(
        npz_path,
        matrix=matrix,
        case_ids=np.array(case_ids),
    )
    write_jsonl(index_dir / "example_bank.jsonl", cases)
    write_json(
        index_dir / "index_meta.json",
        {
            "n_cases": len(cases),
            "embed_dim": int(matrix.shape[1]),
            "embed_model": client.embed_model,
            "chat_model": client.chat_model,
        },
    )
    print("Wrote cache/index/cases_with_embeddings.npz and example_bank.jsonl")
    print(f"LLM stats: {client.stats}")


if __name__ == "__main__":
    main()
