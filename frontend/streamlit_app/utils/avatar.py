"""Validate external avatar references without fetching or resolving them."""

from __future__ import annotations

import re
from ipaddress import ip_address
from unicodedata import category
from urllib.parse import unquote, urlsplit


def external_avatar_url(value: object) -> str | None:
    """Accept HTTPS URLs with a valid external host and no credentials/controls."""
    if not isinstance(value, str) or not value:
        return None
    if "\\" in value or any(
        character.isspace() or category(character) in {"Cc", "Cf"}
        for character in value
    ):
        return None
    if any(category(character) in {"Cc", "Cf"} for character in unquote(value)):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or (parsed.port is not None and not 1 <= parsed.port <= 65535)
        ):
            return None
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except (ValueError, UnicodeError):
        return None
    if "%" in host:
        return None

    try:
        address = ip_address(host)
    except ValueError:
        labels = host.split(".")
        if (
            len(labels) < 2
            or len(host) > 253
            or labels[-1].isdigit()
            # Browsers interpret a hexadecimal final label as an IPv4 number.
            or re.fullmatch(r"0x[0-9a-f]*", labels[-1]) is not None
            or host.endswith((".localhost", ".local"))
            or any(
                not label
                or len(label) > 63
                or not label[0].isalnum()
                or not label[-1].isalnum()
                or any(
                    not (character.isalnum() or character == "-") for character in label
                )
                for label in labels
            )
        ):
            return None
    else:
        if not address.is_global:
            return None
    return value
