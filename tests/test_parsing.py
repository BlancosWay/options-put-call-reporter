from datetime import date

import pytest

from reporter.parsing import ParseError, parse_expiration_label, parse_float, parse_int, parse_percent


def test_parse_percent_removes_percent_symbol() -> None:
    assert parse_percent("31.62%") == 31.62
    assert parse_percent("") is None
    assert parse_percent("—") is None


def test_parse_int_removes_commas() -> None:
    assert parse_int("154,342") == 154342
    assert parse_int("0") == 0


def test_parse_float_handles_commas_and_zero() -> None:
    assert parse_float("1.49") == 1.49
    assert parse_float("2,001.5") == 2001.5


def test_parse_expiration_label_detects_monthly() -> None:
    parsed = parse_expiration_label("06/18/26 (m)")
    assert parsed.expiration_date == date(2026, 6, 18)
    assert parsed.is_monthly is True


def test_parse_expiration_label_detects_weekly() -> None:
    parsed = parse_expiration_label("06/05/26 (w)")
    assert parsed.expiration_date == date(2026, 6, 5)
    assert parsed.is_monthly is False


def test_parse_expiration_label_rejects_bad_value() -> None:
    with pytest.raises(ParseError, match="expiration"):
        parse_expiration_label("June 2026")


def test_parse_expiration_label_rejects_invalid_calendar_date() -> None:
    with pytest.raises(ParseError, match="expiration"):
        parse_expiration_label("13/40/26 (m)")

