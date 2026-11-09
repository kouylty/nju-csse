"""UTC time and storage formatting, replaceable in tests."""

from datetime import UTC, datetime


def now() -> datetime:
    return datetime.now(UTC)


def timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds")
