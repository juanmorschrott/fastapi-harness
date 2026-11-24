import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from fastapi_harness.cli import CLI
from fastapi_harness.config import HarnessConfig


@pytest.fixture
def project(tmp_path: Path) -> Path:
    package = tmp_path / "src" / "app"
    for relative in ("", "users", "orders"):
        folder = package / relative
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "__init__.py").write_text("", encoding="utf-8")
    return tmp_path


def run_check(project: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "fastapi_harness.cli", "check", "--path", str(project)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )


def test_install_detects_modules_and_is_idempotent(project: Path) -> None:
    cli = CLI()
    assert cli.run(["init", "--path", str(project), "--dry-run"]) == 0
    assert not (project / "harness.yaml").exists()
    assert cli.run(["init", "--path", str(project)]) == 0
    data = yaml.safe_load((project / "harness.yaml").read_text())
    assert data["package"] == "app"
    assert data["modules"] == ["orders", "users"]
    assert "MCP" in (project / "AGENTS.md").read_text()
    assert "https://modelcontextprotocol.io/" in (project / "docs/conventions.md").read_text()
    architecture = (project / "docs/architecture.md").read_text()
    assert "src/" in architecture
    assert "router.py" in architecture and "schemas.py" in architecture
    assert (project / "docs/specs/00-harness.md").is_file()
    assert "Mermaid" in (project / "docs/specs/feature-template.md").read_text()
    assert "Do not modify files" in (
        project / "skills/fastapi-review/SKILL.md"
    ).read_text()
    assert cli.run(["init", "--path", str(project)]) == 0
    assert run_check(project).returncode == 0


def test_conflict_does_not_write_any_files(project: Path) -> None:
    (project / "AGENTS.md").write_text("Existing instructions")
    assert CLI().run(["init", "--path", str(project)]) == 1
    assert (project / "AGENTS.md").read_text() == "Existing instructions"
    assert not (project / "harness.yaml").exists()


def test_generated_guidance_includes_fastapi_practices(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    conventions = (project / "docs/conventions.md").read_text()
    review = (project / "skills/fastapi-review/SKILL.md").read_text()
    for practice in (
        "request and response schemas",
        "FastAPI dependencies",
        "typed settings",
        "thread pool",
        "durable queue",
        "versioned migrations",
        "async HTTPX client",
    ):
        assert practice in conventions
    assert "does not verify API" in conventions
    assert "https://peps.python.org/pep-0008/" in conventions
    assert "https://fastapi.tiangolo.com/" in conventions
    assert "https://github.com/zhanymkanov/fastapi-best-practices" in conventions
    assert "migrations" in review and "background task" in review


def test_generated_guidance_links_resolve(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    for path in [project / "AGENTS.md", *project.glob("docs/**/*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if not target.startswith(("https://", "http://", "#")):
                assert (path.parent / target).is_file(), (path, target)


def test_cross_domain_imports_pass(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/users/service.py").write_text(
        "from app.orders import service\n\n\n"
        "def get_value() -> int:\n    return service.get_value()\n"
    )
    (project / "src/app/orders/service.py").write_text(
        "def get_value() -> int:\n    return 1\n"
    )
    result = run_check(project)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("code", "diagnostic"),
    [
        ("def identity(value):\n    return value\n", "no-untyped-def"),
        ("def identity(value: int) -> str:\n    return value\n", "return-value"),
        ("import os\n", "F401"),
        ("value: int=1\n", "would be reformatted"),
    ],
)
def test_quality_checks_fail(project: Path, code: str, diagnostic: str) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/users/example.py").write_text(code)
    result = run_check(project)
    assert result.returncode != 0
    assert diagnostic in result.stdout + result.stderr


def test_project_mypy_config_cannot_disable_strict_checks(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "mypy.ini").write_text("[mypy]\ndisallow_untyped_defs = False\n")
    (project / "src/app/users/example.py").write_text(
        "def identity(value):\n    return value\n"
    )
    result = run_check(project)
    assert result.returncode != 0
    assert "no-untyped-def" in result.stdout + result.stderr


def test_complexity_fails(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    code = "def complex_function(value):\n" + "".join(
        f"    if value == {n}: return {n}\n" for n in range(11)
    ) + "    return None\n"
    (project / "src/app/users/complex.py").write_text(code)
    result = run_check(project)
    assert result.returncode != 0
    assert 'has a rank of C' in result.stderr


def test_single_module_is_supported(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project), "--modules", "users", "orders"]) == 0
    data = yaml.safe_load((project / "harness.yaml").read_text())
    data["modules"] = ["users"]
    (project / "harness.yaml").write_text(yaml.safe_dump(data))
    for path in (project / "src/app/orders").rglob("*"):
        if path.is_file():
            path.unlink()
    (project / "src/app/orders").rmdir()
    result = run_check(project)
    assert result.returncode == 0, result.stdout + result.stderr


def test_detects_new_unconfigured_module(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    new = project / "src/app/new"
    new.mkdir()
    (new / "__init__.py").write_text("")
    result = run_check(project)
    assert result.returncode != 0
    assert "modules differ" in result.stderr


def test_missing_package_and_empty_module_list_fail(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/users/__init__.py").unlink()
    assert "modules differ" in run_check(project).stderr
    (project / "harness.yaml").write_text(
        "schema_version: 2\npackage: app\nsource: src\nmodules: []\n"
    )
    assert "at least one module" in run_check(project).stderr


def test_legacy_config_is_rejected(project: Path) -> None:
    (project / "harness.yaml").write_text(
        "schema_version: 1\npackage: app\nsource: src\nmodules: [users]\n"
    )
    result = run_check(project)
    assert result.returncode != 0
    assert "migrate to the version 2 domain layout" in result.stderr


@pytest.mark.parametrize(
    "values",
    [
        {"package": "class"},
        {"package": "app", "source": "../outside"},
        {"package": "app", "modules": ["users", "users"]},
        {"package": "app", "unknown": 1},
        {"package": "app", "quality": {"max_absolute": "Z"}},
        {"package": "app", "schema_version": True},
    ],
)
def test_invalid_config_is_rejected(values: dict) -> None:
    with pytest.raises(ValueError):
        HarnessConfig.model_validate(values)
