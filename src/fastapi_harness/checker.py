import os
import subprocess
import tempfile
from pathlib import Path

from .config import HarnessConfig


class Checker:
    def __init__(self, root: Path, config: HarnessConfig):
        self.root = root.resolve()
        self.config = config

    def validate_layout(self) -> Path:
        source = (self.root / self.config.source).resolve()
        if not source.is_relative_to(self.root) or not source.is_dir():
            raise ValueError("source must be an existing directory inside the project")
        package = source / self.config.package
        if not package.resolve().is_relative_to(self.root):
            raise ValueError("package must be inside the project")
        if not (package / "__init__.py").is_file():
            raise ValueError("package must contain __init__.py")
        self.validate_modules(package)
        return source

    def validate_modules(self, modules_dir: Path) -> None:
        if not self.config.modules:
            raise ValueError("configure at least one module before running architecture checks")
        discovered = self.discover_modules(modules_dir)
        configured = set(self.config.modules)
        if discovered != configured:
            raise ValueError(
                f"modules differ from configuration: found={sorted(discovered)}, "
                f"configured={sorted(configured)}"
            )
        for name in self.config.modules:
            module = modules_dir / name
            if not module.resolve().is_relative_to(self.root):
                raise ValueError(f"module escapes project: {name}")

    @staticmethod
    def discover_modules(modules_dir: Path) -> set[str]:
        discovered = set()
        for path in modules_dir.iterdir():
            if path.name.startswith((".", "_")):
                continue
            if path.is_dir() and (path / "__init__.py").is_file():
                discovered.add(path.name)
        return discovered

    def run(self) -> int:
        source = self.validate_layout()
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(source), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])]
        )
        env["MYPYPATH"] = os.pathsep.join(
            [str(source), *([env["MYPYPATH"]] if env.get("MYPYPATH") else [])]
        )
        with tempfile.TemporaryDirectory(prefix="fastapi-harness-") as directory:
            mypy_config = Path(directory) / "mypy.ini"
            mypy_config.write_text("[mypy]\n", encoding="utf-8")
            commands = [
                [
                    "xenon", "--max-absolute", self.config.quality.max_absolute,
                    "--max-modules", self.config.quality.max_modules,
                    "--max-average", self.config.quality.max_average,
                    str(source / self.config.package),
                ],
                [
                    "mypy", "--config-file", str(mypy_config), "--strict", "--no-incremental",
                    str(source / self.config.package),
                ],
                [
                    "ruff", "check", "--isolated", "--select", "E,F",
                    str(source / self.config.package),
                ],
                ["ruff", "format", "--isolated", "--check", str(source / self.config.package)],
            ]
            failed = False
            for command in commands:
                print("+ " + " ".join(command), flush=True)
                result = subprocess.run(command, cwd=self.root, env=env, check=False)
                failed |= result.returncode != 0
        return int(failed)
