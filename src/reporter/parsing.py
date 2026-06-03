from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedExpiration:
    expiration_date: date
    is_monthly: bool


def parse_percent(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip().replace("%", "")
    if cleaned in {"", "—", "-", "N/A"}:
        return None
    try:
        return float(cleaned.replace(",", ""))
    except ValueError as exc:
        raise ParseError(f"Cannot parse percent from '{value}'") from exc


def parse_int(value: str) -> int:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", "—", "-", "N/A"}:
        raise ParseError(f"Cannot parse integer from '{value}'")
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ParseError(f"Cannot parse integer from '{value}'") from exc


def parse_float(value: str) -> float:
    cleaned = value.strip().replace(",", "")
    if cleaned in {"", "—", "-", "N/A"}:
        raise ParseError(f"Cannot parse float from '{value}'")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ParseError(f"Cannot parse float from '{value}'") from exc


def parse_expiration_label(value: str) -> ParsedExpiration:
    cleaned = " ".join(value.strip().split())
    match = re.match(r"^(?P<month>\d{2})/(?P<day>\d{2})/(?P<year>\d{2})\s+\((?P<kind>[mw])\)$", cleaned)
    if not match:
        raise ParseError(f"Cannot parse expiration label '{value}'")
    try:
        expiration_date = datetime.strptime(
            f"{match.group('month')}/{match.group('day')}/{match.group('year')}",
            "%m/%d/%y",
        ).date()
    except ValueError as exc:
        raise ParseError(f"Cannot parse expiration label '{value}'") from exc
    return ParsedExpiration(
        expiration_date=expiration_date,
        is_monthly=match.group("kind") == "m",
    )
