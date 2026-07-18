"""Registry of the available legacy-encoding conversion tables.

New encodings register their :class:`~viparse.normalize.tables.Charmap` here so
the detector and normalizer can look them up by name.
"""

from __future__ import annotations

from viparse.normalize.tables import Charmap
from viparse.normalize.tcvn3 import TCVN3
from viparse.normalize.viscii import VISCII
from viparse.normalize.vni import VNI
from viparse.normalize.vps import VPS


def _register(*charmaps: Charmap) -> dict[str, Charmap]:
    """Index charmaps by name, raising if two share a name (a copy-paste slip)."""
    registry: dict[str, Charmap] = {}
    for charmap in charmaps:
        if charmap.name in registry:
            raise ValueError(f"duplicate encoding name {charmap.name!r}")
        registry[charmap.name] = charmap
    return registry


CHARMAPS: dict[str, Charmap] = _register(TCVN3, VNI, VISCII, VPS)

# Candidates for content-frequency auto-detection (SPEC-3 E3.2). VPS is deliberately
# excluded: it keys the same Latin-1 surface bytes as VISCII to *different* Vietnamese
# letters, so offering it as a trial candidate lets a genuine VISCII document be mis-scored
# as VPS and silently corrupted — the moat's cardinal sin. Its uppercase letters also live
# in C0 control bytes that cleanup strips before detection, making auto-detection of VPS
# unreliable regardless. VPS therefore converts only via an explicit ``encoding="vps"``
# override, never by auto-detection.
AUTO_DETECT_CHARMAPS: dict[str, Charmap] = {
    name: charmap for name, charmap in CHARMAPS.items() if name != VPS.name
}


def get_charmap(name: str) -> Charmap | None:
    """Return the registered charmap for ``name``, or ``None`` if unknown."""
    return CHARMAPS.get(name)
