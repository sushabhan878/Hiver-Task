# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- MIT `LICENSE`.
- Production repository scaffolding: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, `SUPPORT.md`, `AGENTS.md`.
- Tooling configuration: `pyproject.toml` (project metadata, ruff lint +
  format, mypy, pytest, coverage), `.prettierrc` + `.prettierignore` for the
  Markdown/YAML layer, `.editorconfig`, `.gitattributes`.
- Git hygiene: commit-message template (`.gitmessage.txt`), Conventional
  Commits policy, extended `.gitignore`.
- CI: GitHub Actions workflow running lint, format check, type check, tests
  with coverage, and a warm-cache reproduction smoke test.
- Dependency hygiene: `requirements-dev.txt`, Dependabot config,
  `CODEOWNERS`.

[Unreleased]: https://github.com/your-org/supportpilot/compare/v0.1.0...HEAD
