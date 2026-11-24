# <img src="https://cdn.simpleicons.org/fastapi/009688" alt="" width="32" height="32"> FastAPI Harness

**Give your AI agent the context and guardrails to build consistent FastAPI
applications.**

[![CI](https://github.com/juanmorschrott/fastapi-harness/actions/workflows/checks.yml/badge.svg)](https://github.com/juanmorschrott/fastapi-harness/actions/workflows/checks.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

FastAPI Harness installs an opinionated set of instructions, specifications,
and automated checks into your project. Describe a feature directly or in a
specification, then let your preferred AI agent implement it within a defined
architecture.

Its goal is to create that harness **automatically and deterministically**:
given the same harness version and project configuration, initialization
renders the same guidance and reports conflicts instead of overwriting files.
The CLI does not use an AI agent to generate the harness.

This is an independent community project. It is not affiliated with or endorsed
by FastAPI or the authors of FastAPI Best Practices.

> **Early-stage project:** designed primarily for new FastAPI applications.
> The harness does not generate application code, migrate existing projects,
> invoke agents, or replace human review.

## How it works

```text
Your requirements
        |
        v
  Direct request or spec  -->  External AI agent  -->  Implementation
                                   |                       |
                                   v                       v
                          Harness instructions       Automated checks
```

1. **Install the harness** into a project that follows the expected layout.
2. **Describe the feature** in a Markdown specification or a direct request.
3. **Ask your agent to implement it**, pointing it to `AGENTS.md` and the
   relevant requirements.
4. **Verify the result** with `fastapi-harness check` and your project's tests.
   Ask the agent to report failures and anything it could not verify.

## Quick start

### 1. Install

From a local checkout, install the CLI with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install .
```

Alternatively, run `pip install .` from the checkout to install into the active
Python environment. For checks that need your application's dependencies,
prefer installing the harness in the project's environment: an isolated
`uv tool` environment does not automatically include those dependencies.

Once published, the CLI can also be run with `uvx fastapi-harness init`. For
reproducible CI, pin a released harness version as a development dependency.

### 2. Prepare your project

The harness expects a Python package with at least one domain package:

```text
src/
└── app/
    ├── __init__.py
    ├── main.py
    └── users/
        ├── __init__.py
        ├── router.py
        ├── schemas.py
        └── service.py
```

This is an example, not generated application code. The generated architecture
document includes a more detailed reference tree and layer responsibilities.

### 3. Initialize and check

From the target project's root:

```bash
fastapi-harness init --dry-run  # Preview files
fastapi-harness init            # Install guidance
fastapi-harness check           # Run automated guardrails
```

`init` discovers a single top-level package in `src/` or the current directory,
and domain packages directly under `app/`. If detection is ambiguous, specify
the package and source; modules can also be selected explicitly:

```bash
fastapi-harness init --package app --source src --modules users orders
```

Use `--path` with either command to select another project directory.
`harness.yaml` must list **all** direct subpackages. A missing module list or
unlisted module is an error.

**Your files are protected:** initialization does not overwrite differing
files; it reports conflicts without writing anything. Identical files are left
untouched. To update guidance from a newer harness version, review and update
existing files manually.

The domain-oriented layout uses configuration schema version 2. Version 1
configurations are rejected rather than silently interpreted with new rules;
move application code to the new layout and update `harness.yaml` and the
generated guidance manually.

## What gets installed

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Entry point for agent instructions |
| `docs/architecture.md` | Reference layout, layers, and boundaries |
| `docs/conventions.md` | FastAPI, Python, and agent-tooling conventions |
| `docs/specs/` | Harness specification and feature specification template |
| `skills/fastapi-feature/SKILL.md` | Feature implementation workflow |
| `skills/fastapi-review/SKILL.md` | Read-only review workflow |
| `harness.yaml` | Package, modules, and complexity configuration |

Agents differ in which instructions and skills they discover automatically.
Point your agent to `AGENTS.md` explicitly when needed. The harness does not
install or configure MCP servers; use only approved tools and protect secrets.

## Work from a specification

Copy `docs/specs/feature-template.md` in your target project and describe the
feature's observable behavior, edge cases, and acceptance criteria. For
example, a CRUD specification might include an entity diagram alongside the
endpoint contracts, validation rules, and error responses.
The generated `docs/specs/example-crud.md` illustrates this format; it is not
a requirement to implement.

An entity-relationship diagram, including Mermaid, does **not** define API
behavior, persistence, authorization, or deletion rules by itself. State those
decisions explicitly or have the agent ask for clarification.

To review changes without applying fixes, ask the agent to follow
`skills/fastapi-review/SKILL.md`. Compatible agents may expose it as
`/fastapi-review`; discovery and invocation depend on the agent.

## Automated guardrails

`fastapi-harness check` validates the application package:

| Check | Tool | What it covers |
| --- | --- | --- |
| Layout | Harness | Application package and domain registration |
| Complexity | Xenon | Configured cyclomatic complexity limits |
| Types | MyPy | Strict type checking |
| Style | Ruff | E and F lint rules and formatting |

All checks are mandatory, and a failure produces a nonzero exit code. MyPy and
Ruff use harness-owned settings rather than the project's tool configuration;
Ruff's defaults include an 88-character line length. Adding the harness to an
existing project can therefore introduce new failures. Ruff checks selected
style rules inspired by [PEP 8](https://peps.python.org/pep-0008/), not full
PEP 8 compliance.

**Know the limits:** the harness does not enforce architectural or import
boundaries, and inline suppressions can affect results. `check` does not
run tests, validate every FastAPI practice, or verify OpenTelemetry. No tests,
telemetry, or CI configuration are installed automatically. Run relevant tests
separately and review requirements that cannot be checked automatically.
For framework guidance, consult the
[official FastAPI documentation](https://fastapi.tiangolo.com/).

## Developing the harness

This repository is a CLI package, not a FastAPI application. Its own
architecture and import contracts differ from the guidance it generates;
`fastapi-harness check` does not apply to its source.

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run lint-imports
uv run xenon --max-absolute B --max-modules A --max-average A src/fastapi_harness
```

See [architecture](docs/architecture.md) and [conventions](docs/conventions.md)
for repository guidance.

## Acknowledgments

Thanks to [Yerassyl (@zhanymkanov)](https://github.com/zhanymkanov) and the
contributors of
[FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices)
for sharing their experience and recommendations with the community. The
generated conventions adapt selected ideas to this harness's architecture.

## License

[MIT](LICENSE)
