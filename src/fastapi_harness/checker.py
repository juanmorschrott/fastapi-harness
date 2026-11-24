import os
import subprocess
import tempfile
from pathlib import Path

from jinja2 import Environment, PackageLoader, StrictUndefined

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
        modules_dir = package / "modules"
        self.validate_packages(package, modules_dir)
        self.validate_modules(modules_dir)
        return source

    def validate_packages(self, package: Path, modules_dir: Path) -> None:
        if not package.resolve().is_relative_to(self.root) or not modules_dir.resolve().is_relative_to(self.root):
            raise ValueError("package and modules must be inside the project")
        if not (package / "__init__.py").is_file() or not (modules_dir / "__init__.py").is_file():
            raise ValueError("package and its modules directory must contain __init__.py")

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
            self.validate_layers(module)

    @staticmethod
    def discover_modules(modules_dir: Path) -> set[str]:
        discovered = set()
        for path in modules_dir.iterdir():
            if path.name.startswith((".", "_")):
                continue
            if path.is_dir():
                if not (path / "__init__.py").is_file():
                    raise ValueError(f"module is missing __init__.py: {path}")
                discovered.add(path.name)
            elif path.suffix == ".py":
                raise ValueError(f"feature module must be a package, not a file: {path}")
        return discovered

    @staticmethod
    def validate_layers(module: Path) -> None:
        for layer in ("routers", "services", "repositories"):
            if not (module / layer / "__init__.py").is_file():
                raise ValueError(f"missing package: {module / layer}")

    def run(self) -> int:
        source = self.validate_layout()
        environment = Environment(
            loader=PackageLoader("fastapi_harness", "templates"),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )
        contract = environment.get_template("importlinter.ini.j2").render(
            config=self.config,
            has_shared=(source / self.config.package / "shared" / "__init__.py").is_file(),
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(source), *([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])]
        )
        env["MYPYPATH"] = os.pathsep.join(
            [str(source), *([env["MYPYPATH"]] if env.get("MYPYPATH") else [])]
        )
        with tempfile.TemporaryDirectory(prefix="fastapi-harness-") as directory:
            config_file = Path(directory) / ".importlinter"
            config_file.write_text(contract, encoding="utf-8")
            mypy_config = Path(directory) / "mypy.ini"
            mypy_config.write_text("[mypy]\n", encoding="utf-8")
            commands = [
                ["lint-imports", str(config_file)],
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
