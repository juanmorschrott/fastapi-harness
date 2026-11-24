# Architecture

This repository is a CLI tool, not a FastAPI application. Do not invent
routers, services or repositories for it. The generated guidance describes that
architecture for target applications.

The CLI orchestrates the installer and checker; both depend on configuration
but not on each other. Templates are packaged resources. The import-linter
contract in `pyproject.toml` checks these boundaries.

Keep the design direct: use classes for behavior, except required framework
entry points and test functions. Avoid speculative abstractions. Installation
must preserve existing files; validation must report incomplete configuration
and failed checks rather than silently passing.
