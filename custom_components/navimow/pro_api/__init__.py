"""Navimow private-cloud API (crypto + passport + client).

This package is vendored from ilguala/navimow_pro
(https://github.com/ilguala/navimow_pro), MIT License,
Copyright (c) 2026 Roberto Gualandris. See the LICENSE file in this directory.

It provides the signed + envelope-encrypted client for the Segway Navimow
private app cloud, used here only to read extra device data (blade/chassis
service life, schedule, settings) that the official OAuth API does not expose.
"""
from __future__ import annotations

from .client import (
    NavimowAuthError,
    NavimowCloudClient,
    NavimowError,
)
from .passport import (
    RESULT_ACCOUNT_NOT_EXISTS,
    PassportAuthError,
    PassportError,
    Tokens,
)

__all__ = [
    "NavimowAuthError",
    "NavimowCloudClient",
    "NavimowError",
    "PassportAuthError",
    "PassportError",
    "RESULT_ACCOUNT_NOT_EXISTS",
    "Tokens",
]
