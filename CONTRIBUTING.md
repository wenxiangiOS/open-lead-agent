# Contributing

Thanks for taking a look at `open-lead-agent`.

This project aims to stay small, understandable, and easy to extend. A good
contribution should make the configurable agent engine more useful without
locking it to one business domain.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

Run the API locally:

```bash
uvicorn main:app --reload
```

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

## Contribution Guidelines

- Keep behavior configurable through templates when possible.
- Keep modules small and replaceable.
- Add or update tests for behavior changes.
- Do not commit secrets, private templates, or production customer data.
- Keep README and docs aligned with what the code actually supports.

## Pull Requests

Before opening a pull request:

1. Run `pytest`.
2. Run `ruff check .`.
3. Describe the user-facing change.
4. Mention any compatibility impact on existing templates or API responses.
