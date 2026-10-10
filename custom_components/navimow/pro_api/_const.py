"""Region and host constants for the Navimow private-cloud API.

Vendored from ilguala/navimow_pro (MIT, (c) 2026 Roberto Gualandris); see the
LICENSE file in this directory. Extracted here so the pro_api package is
self-contained and independent of this integration's own const.py.
"""
from __future__ import annotations

from typing import Final

DEFAULT_REGION: Final = "fra"
REGION_AUTO: Final = "auto"  # config-flow choice: detect from the account

# Codes the backend also answers to, mapped onto the primary code. "ore"
# (Oregon) is what a US account reports back and resolves to the same server
# as "us".
_REGION_ALIASES: Final = {"eu": "fra", "sea": "sg", "ore": "us"}

PASSPORT_HOSTS: Final = {
    "fra": ("api-passport-fra.willand.com", "api-passport-fra.ninebot.com"),
    "sg": ("api-passport-sg.willand.com", "api-passport-sg.ninebot.com"),
    "us": (
        "api-passport-us.ninebot.com",
        "api-passport-ore.ninebot.com",
        "api-passport-ore.willand.com",
    ),
    "bj": ("api-passport-bj.willand.com", "api-passport-bj.ninebot.com"),
}

# Mower-cloud candidates per region, tried in order; the first that answers is
# persisted. There is no navimow-us* host: a US account's mower data is served
# by the Frankfurt host.
MOWER_HOSTS: Final = {
    "fra": ("navimow-fra.ninebot.com", "navimow-fra.willand.com"),
    "sg": ("navimow-sg.willand.com",),
    "bj": ("navimow-bj.ninebot.com", "navimow-bj.willand.com"),
    "us": ("navimow-fra.ninebot.com", "navimow-ore.willand.com"),
}

REGIONS: Final = tuple(PASSPORT_HOSTS)

_ALL_MOWER_HOSTS: Final = tuple(
    dict.fromkeys(h for hosts in MOWER_HOSTS.values() for h in hosts)
)

# Order to ask "which region owns this account?": the primary host of each
# region first (so every region is covered in 4 calls), then the secondaries.
ALL_PASSPORT_HOSTS: Final = tuple(
    dict.fromkeys(
        [hosts[0] for hosts in PASSPORT_HOSTS.values() if hosts]
        + [h for hosts in PASSPORT_HOSTS.values() for h in hosts[1:]]
    )
)


def canonical_region(region: str | None) -> str:
    """Normalise a region code ('EU' -> 'fra'); unknown codes are kept as-is."""
    code = str(region or "").strip().lower()
    if not code:
        return DEFAULT_REGION
    return _REGION_ALIASES.get(code, code)


def passport_hosts(region: str | None) -> tuple[str, ...]:
    """Passport hosts to try for a region (all of them if the code is unknown)."""
    return PASSPORT_HOSTS.get(canonical_region(region)) or ALL_PASSPORT_HOSTS


def mower_hosts(region: str | None) -> tuple[str, ...]:
    """Mower-cloud hosts to try for a region.

    Falls back to every known host when the region has none mapped ("us") or is
    unrecognised, so a new/unknown region degrades to "try everything".
    """
    hosts = MOWER_HOSTS.get(canonical_region(region)) or ()
    extra = tuple(h for h in _ALL_MOWER_HOSTS if h not in hosts)
    return hosts + extra


def encode_partition_ids(region_ids: list[int]) -> str:
    """Encode region ids as concatenated little-endian uint16 hex.

    Region id 1 -> "0100", 5 -> "0500", [1,5] -> "01000500".
    """
    out = []
    for rid in region_ids:
        out.append(f"{rid & 0xFF:02x}{(rid >> 8) & 0xFF:02x}")
    return "".join(out)
