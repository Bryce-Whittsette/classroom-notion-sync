# Contributing

Thanks for helping improve Classroom → Notion.

## Local setup

Use Python 3.11 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Tests must not require live Google or Notion credentials. Use mocks or fixtures for service behavior, and never commit `.env`, `credentials.json`, or `token.json`.

## Making a change

1. Open an issue for behavior changes that affect sync semantics or the Notion schema.
2. Create a focused branch and keep the patch small.
3. Add or update tests for status precedence, pagination, duplicate detection, protected fields, and dry-run behavior as appropriate.
4. Run the full test suite before opening a pull request.
5. Update `README.md` for user-facing changes and add a concise entry under **Unreleased** in `CHANGELOG.md`.

Pull requests should explain the problem, the chosen behavior, test evidence, and any migration or credential impact.
