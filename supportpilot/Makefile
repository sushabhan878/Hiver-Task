.PHONY: help reproduce all env data corpus labels index golden evaluate baselines calibrate tests clean check lint format typecheck coverage precommit

help:
	@echo "SupportPilot targets:"
	@echo "  make reproduce   - full one-command evaluation (uses caches when present)"
	@echo "  make check       - verify environment (python deps + ollama models)"
	@echo "  make data        - download raw dataset mirrors into data/raw"
	@echo "  make corpus      - brand profiling + conversation corpus + splits"
	@echo "  make labels      - LLM intent labelling of retrieval corpus (slow, cached)"
	@echo "  make index       - embed labelled cases, build retrieval index"
	@echo "  make golden      - sample + assisted hand-annotation of golden set"
	@echo "  make evaluate    - agent + baselines + judge on golden set"
	@echo "  make tests       - unit + integration tests"
	@echo "  make lint        - ruff lint + format check"
	@echo "  make format      - ruff autofix + format the tree"
	@echo "  make typecheck   - mypy on src/"
	@echo "  make coverage    - pytest with coverage report"
	@echo "  make precommit   - run pre-commit hooks on all files"
	@echo ""
	@echo "No make? The single command is: python -m scripts.reproduce"

check:
	python -m scripts.check_env
	python -m pytest tests -q

lint:
	python -m ruff check src scripts tests
	python -m ruff format --check src scripts tests

format:
	python -m ruff check src scripts tests --fix
	python -m ruff format src scripts tests

typecheck:
	python -m mypy src

coverage:
	python -m pytest tests --cov=src --cov-report=term-missing

precommit:
	python -m pre_commit run --all-files

data:
	python -m scripts.download_data

corpus:
	python -m scripts.profile_dataset
	python -m scripts.build_corpus

labels:
	python -m scripts.label_corpus

index:
	python -m scripts.build_index

golden:
	python -m scripts.sample_golden --n 200
	python -m scripts.evaluate --draft
	python -m scripts.annotate_golden
	@echo "Hand-annotate data/golden/golden_annotated_draft.jsonl overrides, then:"
	@echo "  python -m scripts.annotate_golden --finalize"

evaluate:
	python -m scripts.evaluate --systems agent,b1,b2,b3
	python -m scripts.calibrate_judge
	python -m scripts.analyze_failures

reproduce: check
	python -m scripts.reproduce
	@echo "Reproduction complete. See reports/results.json and reports/final_report.md"

tests:
	python -m pytest tests -q

clean:
	@echo "Caches in cache/ can be deleted to force full recomputation (slow)."
	@echo "Tooling caches (.ruff_cache, .mypy_cache, .pytest_cache) are gitignored."

# quality gate bundle: everything CI runs except the Ollama-dependent stages
all: lint typecheck tests
