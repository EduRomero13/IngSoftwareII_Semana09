from datetime import datetime, timezone


def utcnow() -> datetime:
    """UTC naive (consistente con DateTime sin tz de la base de datos)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
