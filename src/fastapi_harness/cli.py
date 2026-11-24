import argparse
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from .checker import Checker
from .config import HarnessConfig
from .installer import Installer


class CLI:
    def run(self, arguments: list[str] | None = None) -> int:
        args = self.parse_arguments(arguments)
        try:
            if not args.path.is_dir():
                raise ValueError("project path must be an existing directory")
            if args.command == "check":
                return Checker(args.path, HarnessConfig.load(args.path / "harness.yaml")).run()
            return self.init(args)
        except (ValueError, OSError, yaml.YAMLError, ValidationError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1

    @staticmethod
    def parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(prog="fastapi-harness")
        commands = parser.add_subparsers(dest="command", required=True)
        init = commands.add_parser("init", help="Install harness files without overwriting")
        init.add_argument("--path", type=Path, default=Path.cwd())
        init.add_argument("--package", help="Top-level Python package")
        init.add_argument("--source", help="Directory containing the Python package")
        init.add_argument("--modules", nargs="*", help="Module names (default: discover)")
        init.add_argument("--dry-run", action="store_true")
        check = commands.add_parser("check", help="Check layout, complexity, types and style")
        check.add_argument("--path", type=Path, default=Path.cwd())
        return parser.parse_args(arguments)

    def init(self, args: argparse.Namespace) -> int:
        config = self.build_config(args)
        changes = Installer(args.path, config).install(dry_run=args.dry_run)
        print(("Would create:" if args.dry_run else "Created:") if changes else "Already installed.")
        for name in changes:
            print(f"  {name}")
        if not config.modules:
            print("No modules discovered; configure modules in harness.yaml before check.")
        return 0

    def build_config(self, args: argparse.Namespace) -> HarnessConfig:
        source = args.source or ("src" if (args.path / "src").is_dir() else ".")
        HarnessConfig(package="placeholder", source=source)
        source_path = (args.path / source).resolve()
        if not source_path.is_relative_to(args.path.resolve()) or not source_path.is_dir():
            raise ValueError("source must be an existing directory inside the project")
        package = args.package or self.discover_package(source_path)
        HarnessConfig(package=package, source=source)
        modules_dir = source_path / package
        if not modules_dir.resolve().is_relative_to(args.path.resolve()):
            raise ValueError("package and modules must be inside the project")
        modules = args.modules if args.modules is not None else self.discover_modules(modules_dir)
        return HarnessConfig(package=package, source=source, modules=modules)

    @staticmethod
    def discover_package(source: Path) -> str:
        candidates = [
            item.name for item in source.iterdir()
            if item.is_dir() and (item / "__init__.py").is_file()
            and item.name.isidentifier() and not item.name.startswith("_")
        ]
        if len(candidates) != 1:
            raise ValueError("cannot identify a unique package; pass --package")
        return candidates[0]

    @staticmethod
    def discover_modules(directory: Path) -> list[str]:
        if not directory.is_dir():
            return []
        return sorted(
            path.name for path in directory.iterdir()
            if path.is_dir() and not path.name.startswith((".", "_"))
            and (path / "__init__.py").is_file()
        )


def main() -> None:
    raise SystemExit(CLI().run())


if __name__ == "__main__":
    main()
