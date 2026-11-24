from pathlib import Path
from typing import ClassVar

import yaml
from jinja2 import Environment, PackageLoader, StrictUndefined

from .config import HarnessConfig


class Installer:
    TEMPLATES: ClassVar[dict[str, str]] = {
        "AGENTS.md": "AGENTS.md.j2",
        "docs/architecture.md": "architecture.md.j2",
        "docs/conventions.md": "conventions.md.j2",
        "docs/specs/README.md": "specs.md.j2",
        "docs/specs/00-harness.md": "harness-spec.md.j2",
        "docs/specs/feature-template.md": "spec-template.md.j2",
        "skills/fastapi-feature/SKILL.md": "feature.md.j2",
        "skills/fastapi-review/SKILL.md": "review.md.j2",
    }

    def __init__(self, root: Path, config: HarnessConfig):
        self.root = root.resolve()
        self.config = config
        self.environment = Environment(
            loader=PackageLoader("fastapi_harness", "templates"),
            undefined=StrictUndefined,
            autoescape=False,
            keep_trailing_newline=True,
        )

    def render(self) -> dict[str, str]:
        result = {
            target: self.environment.get_template(template).render(config=self.config)
            for target, template in self.TEMPLATES.items()
        }
        result["harness.yaml"] = yaml.safe_dump(
            self.config.model_dump(), sort_keys=False, allow_unicode=True
        )
        return result

    def install(self, dry_run: bool = False) -> list[str]:
        rendered = self.render()
        conflicts = []
        changes = []
        for name, content in rendered.items():
            path = self.root / name
            if not path.resolve().is_relative_to(self.root):
                raise ValueError(f"path escapes project: {name}")
            if path.exists():
                if not path.is_file() or path.read_text(encoding="utf-8") != content:
                    conflicts.append(name)
            else:
                changes.append(name)
        if conflicts:
            raise FileExistsError(
                "existing files differ; no files written: " + ", ".join(conflicts)
            )
        if not dry_run:
            for name in changes:
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(rendered[name], encoding="utf-8")
        return changes
