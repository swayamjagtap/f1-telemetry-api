from pathlib import Path

from .config import DATA_DIR


SESSION_TYPE_MAP = {
    "FP1": "practice_1",
    "FP2": "practice_2",
    "FP3": "practice_3",
    "Q": "qualifying",
    "S": "sprint",
    "SQ": "sprint_qualifying",
    "R": "race",
}


def normalize_event_name(event_name: str) -> str:
    """Convert an event name into a filesystem-friendly directory name."""
    return event_name.strip().lower().replace(" ", "_")


def get_session_directory(
    year: int,
    event_name: str,
    session_type: str,
) -> Path:
    """Return the directory associated with a session dataset."""

    event_dir = normalize_event_name(event_name)
    session_dir = SESSION_TYPE_MAP.get(
        session_type.upper(),
        session_type.strip().lower(),
    )

    return DATA_DIR / str(year) / event_dir / session_dir