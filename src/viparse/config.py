"""Layered configuration for the load-time defaults (SPEC-5 E5.4).

Defaults are resolved from three sources, **highest precedence first**:

1. per-call function arguments (applied in :mod:`viparse.api`);
2. environment variables ``VIPARSE_<NAME>`` (e.g. ``VIPARSE_OUTPUT=json``);
3. a ``viparse.toml`` file in the working directory (a ``[tool.viparse]`` table, or top-level keys);
4. the built-in defaults.

:func:`load_settings` merges 2–4 into a validated :class:`Settings`; the API layer applies 1
on top. Any bad value raises :class:`~viparse.errors.ConfigError` naming the offending key.
Only stdlib ``tomllib`` is used, so ``core`` gains no dependency.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, get_args

from viparse.errors import ConfigError
from viparse.options import (
    DEFAULT_MAX_BYTES,
    DEFAULT_NORMALIZE_FORM,
    DEFAULT_OUTPUT_FORMAT,
    NormalizeForm,
    OutputFormat,
)

_CONFIG_FILENAME = "viparse.toml"
_ENV_PREFIX = "VIPARSE_"
_KEYS = ("output", "encoding", "ocr", "normalize", "max_bytes")
# Derived from the type aliases (single source of truth — no hand-maintained duplicate list).
_OUTPUT_FORMATS: tuple[OutputFormat, ...] = get_args(OutputFormat)
_NORMALIZE_FORMS: tuple[NormalizeForm, ...] = get_args(NormalizeForm)

_TRUE = frozenset({"true", "1", "yes", "on"})
_FALSE = frozenset({"false", "0", "no", "off"})


class _Unset(Enum):
    """A one-member enum used only for the :data:`UNSET` sentinel (so it types precisely)."""

    UNSET = "unset"


UNSET = _Unset.UNSET
"""Sentinel for a ``load()`` argument the caller did not pass, so the layered default applies.

Distinct from ``None`` (a meaningful value for ``encoding`` / ``ocr``: "no override").
"""


@dataclass(frozen=True, slots=True)
class Settings:
    """The resolved default load options, before per-call overrides are applied.

    Self-validating: constructing a ``Settings`` with a bad value raises
    :class:`~viparse.errors.ConfigError`, so an invalid caller-built ``Settings`` passed to
    ``load(settings=...)`` fails as loudly as an invalid env var / config file would.
    """

    output: OutputFormat = DEFAULT_OUTPUT_FORMAT
    encoding: str | None = None
    ocr: bool | None = None
    normalize: NormalizeForm = DEFAULT_NORMALIZE_FORM
    max_bytes: int = DEFAULT_MAX_BYTES

    def __post_init__(self) -> None:
        if self.output not in _OUTPUT_FORMATS:
            raise ConfigError(f"output must be one of {list(_OUTPUT_FORMATS)}, got {self.output!r}")
        if self.normalize not in _NORMALIZE_FORMS:
            raise ConfigError(
                f"normalize must be one of {list(_NORMALIZE_FORMS)}, got {self.normalize!r}"
            )
        if self.encoding is not None and not isinstance(self.encoding, str):
            raise ConfigError(f"encoding must be a string, got {type(self.encoding).__name__}")
        if self.ocr is not None and not isinstance(self.ocr, bool):
            raise ConfigError(f"ocr must be a boolean, got {self.ocr!r}")
        # bool is an int subclass — reject it explicitly so ``max_bytes = true`` is not an int.
        if isinstance(self.max_bytes, bool) or not isinstance(self.max_bytes, int):
            kind = (
                "a boolean" if isinstance(self.max_bytes, bool) else type(self.max_bytes).__name__
            )
            raise ConfigError(f"max_bytes must be an integer, got {kind}")
        if self.max_bytes <= 0:
            raise ConfigError(f"max_bytes must be positive, got {self.max_bytes}")


def load_settings(
    *, start_dir: Path | None = None, environ: Mapping[str, str] | None = None
) -> Settings:
    """Resolve :class:`Settings` from ``viparse.toml`` then ``VIPARSE_*`` env vars (env wins)."""
    data = _read_config_file(start_dir)
    data.update(_read_env(environ))
    return _build_settings(data)


def _read_config_file(start_dir: Path | None) -> dict[str, Any]:
    directory = start_dir if start_dir is not None else Path.cwd()
    path = directory / _CONFIG_FILENAME
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as handle:
            parsed = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc
    tool = parsed.get("tool")
    if isinstance(tool, dict) and isinstance(tool.get("viparse"), dict):
        # A [tool.viparse] table alongside *any* top-level key is ambiguous — fail loudly
        # rather than silently honoring the table and dropping the top-level keys (which would
        # also hide a typo'd key that isn't in _KEYS). Sibling [tool.*] tables are fine.
        stray = sorted(key for key in parsed if key != "tool")
        if stray:
            raise ConfigError(
                f"{path} has both a [tool.viparse] table and top-level config key(s) "
                f"{stray} — use one form, not both"
            )
        return dict(tool["viparse"])  # embedded [tool.viparse] table
    return {key: value for key, value in parsed.items() if key != "tool"}  # top-level keys


def _read_env(environ: Mapping[str, str] | None) -> dict[str, str]:
    # Only the known keys are read: the environment is a *shared* namespace (other tools, CI
    # systems), so an unrecognized ``VIPARSE_*`` var is ignored rather than rejected. This is
    # deliberately unlike ``viparse.toml`` — that file is viparse's own, so a stray key there
    # is unambiguously a mistake and raises.
    source = environ if environ is not None else os.environ
    return {
        key: source[_ENV_PREFIX + key.upper()]
        for key in _KEYS
        if _ENV_PREFIX + key.upper() in source
    }


def _build_settings(data: Mapping[str, Any]) -> Settings:
    unknown = set(data) - set(_KEYS)
    if unknown:
        raise ConfigError(f"unknown config key(s): {', '.join(sorted(unknown))}")
    # Env values arrive as strings, so coerce the two non-string-typed fields before building
    # Settings — which then validates every field's type and value in __post_init__.
    return Settings(
        output=data.get("output", DEFAULT_OUTPUT_FORMAT),
        encoding=data.get("encoding"),
        ocr=_coerce_bool(data.get("ocr")),
        normalize=data.get("normalize", DEFAULT_NORMALIZE_FORM),
        max_bytes=_coerce_int(data.get("max_bytes", DEFAULT_MAX_BYTES)),
    )


def _coerce_bool(value: Any) -> Any:
    """Turn an env string (``"true"`` / ``"off"`` / …) into a bool; pass other types through."""
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
        raise ConfigError(f"ocr must be a boolean, got {value!r}")
    return value  # bool / None / wrong type — validated by Settings.__post_init__


def _coerce_int(value: Any) -> Any:
    """Turn an env string (``"4096"``) into an int; pass other types through."""
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            raise ConfigError(f"max_bytes must be an integer, got {value!r}") from None
    return value  # int / bool / wrong type — validated by Settings.__post_init__
