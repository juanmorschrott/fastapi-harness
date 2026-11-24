import os
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
    for relative in (
        "",
        "modules",
        "modules/users",
        "modules/users/routers",
        "modules/users/services",
        "modules/users/repositories",
        "modules/orders",
        "modules/orders/routers",
        "modules/orders/services",
        "modules/orders/repositories",
        "shared",
    ):
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
    assert "routers/" in architecture and "repositories/" in architecture
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


@pytest.mark.parametrize(
    ("file", "code"),
    [
        ("users/routers/bad.py", "import app.modules.users.repositories\n"),
        ("users/repositories/bad.py", "import app.modules.users.services\n"),
        ("users/services/bad.py", "import app.modules.orders.services\n"),
    ],
)
def test_forbidden_imports_fail(project: Path, file: str, code: str) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/modules" / file).write_text(code)
    result = run_check(project)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "BROKEN" in result.stdout


def test_shared_import_fails(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/shared/bad.py").write_text("import app.modules.users.services\n")
    result = run_check(project)
    assert result.returncode != 0
    assert "BROKEN" in result.stdout


def test_legitimate_indirect_router_dependency_passes(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    module = project / "src/app/modules/users"
    (module / "routers/route.py").write_text(
        "import app.modules.users.services.service\n\n"
        "print(app.modules.users.services.service)\n"
    )
    (module / "services/service.py").write_text(
        "import app.modules.users.repositories.store\n\n"
        "print(app.modules.users.repositories.store)\n"
    )
    (module / "repositories/store.py").write_text("")
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
    (project / "src/app/modules/users/services/example.py").write_text(code)
    result = run_check(project)
    assert result.returncode != 0
    assert diagnostic in result.stdout + result.stderr


def test_project_mypy_config_cannot_disable_strict_checks(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "mypy.ini").write_text("[mypy]\ndisallow_untyped_defs = False\n")
    (project / "src/app/modules/users/services/example.py").write_text(
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
    (project / "src/app/modules/users/services/complex.py").write_text(code)
    result = run_check(project)
    assert result.returncode != 0
    assert 'has a rank of C' in result.stderr


def test_unlisted_layer_fails(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/modules/users/extra.py").write_text("")
    result = run_check(project)
    assert result.returncode != 0
    assert "BROKEN" in result.stdout


def test_single_module_is_supported(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project), "--modules", "users", "orders"]) == 0
    data = yaml.safe_load((project / "harness.yaml").read_text())
    data["modules"] = ["users"]
    (project / "harness.yaml").write_text(yaml.safe_dump(data))
    for path in (project / "src/app/modules/orders").rglob("*"):
        if path.is_file():
            path.unlink()
    for name in ("routers", "services", "repositories"):
        (project / "src/app/modules/orders" / name).rmdir()
    (project / "src/app/modules/orders").rmdir()
    result = run_check(project)
    assert result.returncode == 0, result.stdout + result.stderr


def test_detects_new_unconfigured_module(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    new = project / "src/app/modules/new"
    new.mkdir()
    (new / "__init__.py").write_text("")
    result = run_check(project)
    assert result.returncode != 0
    assert "modules differ" in result.stderr


def test_missing_layers_and_empty_module_list_fail(project: Path) -> None:
    assert CLI().run(["init", "--path", str(project)]) == 0
    (project / "src/app/modules/users/services/__init__.py").unlink()
    assert "missing package" in run_check(project).stderr
    (project / "harness.yaml").write_text("package: app\nsource: src\nmodules: []\n")
    assert "at least one module" in run_check(project).stderr


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
