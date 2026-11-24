import keyword
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class QualityConfig(StrictModel):
    max_absolute: Literal["A", "B", "C", "D", "E", "F"] = "B"
    max_modules: Literal["A", "B", "C", "D", "E", "F"] = "A"
    max_average: Literal["A", "B", "C", "D", "E", "F"] = "A"


class HarnessConfig(StrictModel):
    schema_version: Literal[1] = 1
    package: str
    source: str = "."
    modules: list[str] = Field(default_factory=list)
    quality: QualityConfig = Field(default_factory=QualityConfig)

    @field_validator("schema_version", mode="before")
    @classmethod
    def validate_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @field_validator("package")
    @classmethod
    def validate_package(cls, value: str) -> str:
        if not value.isidentifier() or keyword.iskeyword(value):
            raise ValueError("package must be a Python identifier, not a keyword")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        path = Path(value)
        if not value or path.is_absolute() or ".." in path.parts:
            raise ValueError("source must be a relative path inside the project")
        return value

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, value: list[str]) -> list[str]:
        for name in value:
            if not name.isidentifier() or keyword.iskeyword(name) or name.startswith("_"):
                raise ValueError(f"invalid module name: {name!r}")
        if len(set(value)) != len(value):
            raise ValueError("module names must be unique")
        return value

    @classmethod
    def load(cls, path: Path) -> "HarnessConfig":
        with path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return cls.model_validate(data)
