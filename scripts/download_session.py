from pathlib import Path
import sys

import fastf1


# ---------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import CACHE_DIR  # noqa: E402
from app.sessions import get_session_directory  # noqa: E402


def load_session(year: int, event: str, session_type: str):
    """
    Load a FastF1 session using the local cache.

    Returns
    -------
    fastf1.core.Session
        Loaded FastF1 session.
    """

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    fastf1.Cache.enable_cache(str(CACHE_DIR))

    print("=" * 60)
    print("F1 TELEMETRY SESSION LOADER")
    print("=" * 60)
    print(f"Year:    {year}")
    print(f"Event:   {event}")
    print(f"Session: {session_type}")
    print()

    session = fastf1.get_session(
        year,
        event,
        session_type,
    )

    print("Loading FastF1 session...")

    session.load(
        telemetry=True,
        weather=True,
        messages=False,
    )

    print()
    print("Session loaded successfully.")
    print(f"Drivers: {len(session.drivers)}")
    print(f"Laps:    {len(session.laps)}")

    return session


def get_output_directory(
    year: int,
    event: str,
    session_type: str,
) -> Path:
    """Return the processed dataset directory."""

    output_dir = get_session_directory(
        year=year,
        event_name=event,
        session_type=session_type,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_dir


if __name__ == "__main__":

    session = load_session(
        year=2025,
        event="Abu Dhabi",
        session_type="Q",
    )

    print()
    print("Session ready for dataset processing.")