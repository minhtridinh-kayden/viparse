"""Registry of the available legacy-encoding conversion tables.

New encodings register their :class:`~viparse.normalize.tables.Charmap` here so
the detector and normalizer can look them up by name.
"""

from __future__ import annotations

from viparse.normalize.tables import Charmap
from viparse.normalize.tcvn3 import TCVN3
from viparse.normalize.vni import VNI


def _register(*charmaps: Charmap) -> dict[str, Charmap]:
    """Index charmaps by name, raising if two share a name (a copy-paste slip)."""
    registry: dict[str, Charmap] = {}
    for charmap in charmaps:
        if charmap.name in registry:
            raise ValueError(f"duplicate encoding name {charmap.name!r}")
        registry[charmap.name] = charmap
    return registry


CHARMAPS: dict[str, Charmap] = _register(TCVN3, VNI)


def get_charmap(name: str) -> Charmap | None:
    """Return the registered charmap for ``name``, or ``None`` if unknown."""
    return CHARMAPS.get(name)
