"""License naming helpers."""

from __future__ import annotations

LICENSE_ALIASES = {
    "Apache License 2.0": "Apache-2.0",
    'BSD 2-Clause "Simplified" License': "BSD-2-Clause",
    'BSD 3-Clause "New" or "Revised" License': "BSD-3-Clause",
    "GNU Affero General Public License v3.0": "AGPL-3.0",
    "GNU General Public License v2.0": "GPL-2.0",
    "GNU General Public License v3.0": "GPL-3.0",
    "GNU Lesser General Public License v2.1": "LGPL-2.1",
    "GNU Lesser General Public License v3.0": "LGPL-3.0",
    "ISC License": "ISC",
    "MIT License": "MIT",
    "Mozilla Public License 2.0": "MPL-2.0",
}


def short_license_name(name: str | None, key: str | None = None) -> str | None:
    if key and key.lower() != "other":
        return key
    if not name:
        return None
    return LICENSE_ALIASES.get(name, name)
