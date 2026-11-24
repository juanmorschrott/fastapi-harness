# fastapi-harness

An opinionated, agent-independent harness for FastAPI projects. It installs
instructions, specifications and quality checks for an AI agent implementing
features in a simple three-layer modular monolith. The agent runs in your
chosen external tool; the harness does not invoke or orchestrate agents.
This package is not the FastAPI CLI and does not change application code.

This is an early first approach, intended primarily for new projects. Applications
must already use the
configured module layout for architecture checks to pass; the harness does not
create or migrate application code automatically.

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

Create the application package and its initial module first, or explicitly pass
`--package` and add the layout before checking. The generated
`docs/architecture.md` contains a reference tree. Add feature requirements
under `docs/specs/`, using `docs/specs/feature-template.md` as a starting
point, or give the agent requirements directly. A Mermaid entity diagram does
not replace decisions about API behavior, persistence or authorization.
The installer does not update existing harness files: if a newer version's
templates differ, review and update them manually.

Point your external agent at `AGENTS.md` and the relevant requirements. Ask it
to implement the feature, run the checks and relevant tests, and report results.
For a read-only review, ask it to follow
`skills/fastapi-review/SKILL.md`; agents that support skill commands may expose
this as `/fastapi-review`. Skill discovery and invocation depend on the agent.

Edit `harness.yaml` to list **all** feature packages under `app/modules`.
Each must contain `routers`, `services` and `repositories` Python packages.
If the existing project differs, migrate it deliberately before running
`check`. A missing module list or missing layers is an error, not a pass.
Use `--path` to select another project directory.

`check` runs import-linter, Xenon, MyPy in strict mode, and Ruff lint (E and F
rules) and format checks on the application package. All checks are
mandatory; adding the harness to an existing project can therefore introduce
new failures. It returns a nonzero exit code if any check fails. MyPy and Ruff
use harness-owned settings rather than the project's tool configuration;
Ruff's defaults include an 88-character line length. Tools may not detect every
violation, and inline suppressions can affect their results.

Contract generation uses the configuration on every run; keep CI on a pinned
harness version. Install the harness in the project's Python environment so
MyPy can resolve application dependencies; an isolated `uv tool` environment
does not automatically include them. Static import checks cannot detect dynamic
imports or all architectural violations. `check` does not run tests, validate all
FastAPI practices, or verify OpenTelemetry. No tests, telemetry or CI
configuration are installed automatically.

The generated `AGENTS.md` and skills use open formats, but agents vary in what
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
