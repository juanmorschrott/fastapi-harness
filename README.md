# fastapi-harness

An opinionated, agent-independent harness for FastAPI projects. It installs
guidance and validates a simple three-layer modular monolith. This package is
not the FastAPI CLI and does not change application code.

This is an early first approach. Existing applications must already use the
configured module layout for architecture checks to pass; the harness does not
migrate them automatically.

## Installation

Install the CLI with [uv](https://docs.astral.sh/uv/) from a local checkout:

```bash
uv tool install .
```

Once the package is published, it can also be run with
`uvx fastapi-harness init`. For reproducible CI, pin a released harness version
as a development dependency in the target project.

The package also supports standard Python tooling: `pip install .` installs it
into the active Python environment.

## Usage

Run from the target project's root:

```bash
fastapi-harness init --dry-run
fastapi-harness init
fastapi-harness check
```

`init` discovers a single top-level package in `src/` (or the current
directory). If detection is ambiguous, specify `--package app --source src`.
Modules are discovered under `app/modules/`; specify `--modules users orders`
to select them explicitly. Installation will not overwrite different files.
Identical files are left untouched. Resolve conflicts manually before retrying.
Existing projects are never reorganized automatically.

Edit `harness.yaml` to list **all** feature packages under `app/modules`.
Each must contain `routers`, `services` and `repositories` Python packages.
If the existing project differs, migrate it deliberately before running
`check`. A missing module list or missing layers is an error, not a pass.
Use `--path` to select another project directory.

`check` runs import-linter and Xenon using the Python package directory and
returns a nonzero exit code on violations. Contract generation uses the
configuration on every run; keep CI on a pinned harness version. Use the same
Python environment for the project and the harness if imports require it.
Static import checks cannot detect dynamic imports or all architectural
violations. No tests or CI configuration are installed automatically.

`AGENTS.md` and the included skills use open formats, but agents vary in what
they discover automatically. Point an agent at `AGENTS.md` if necessary.
The guidance also covers safe use of approved
[MCP](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro)
servers. Installing the harness does not install or configure an MCP server.

For local development:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run lint-imports
uv run xenon --max-absolute B --max-modules A --max-average A src/fastapi_harness
```

This repository uses its own adapted agent guidance and import contracts.
It is a CLI package, not a FastAPI application, so the generated
router/service/repository layout and `fastapi-harness check` do not apply to
the harness's own source code.
