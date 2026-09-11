"""Check Ollama is up and models are pulled before long jobs."""

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:11434"


def main():
    try:
        with urllib.request.urlopen(f"{BASE}/api/tags", timeout=5) as r:
            d = json.loads(r.read())
        names = [m["name"] for m in d.get("models", [])]
        need = ["qwen2.5:3b", "nomic-embed-text"]
        missing = [n for n in need if n not in names and f"{n}:latest" not in names]
        if missing:
            print("Missing models:", missing)
            sys.exit(1)
        print("Ollama ready:", names)
    except Exception as e:
        print(f"Ollama not reachable: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
