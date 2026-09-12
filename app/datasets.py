from pathlib import Path

import pandas as pd

from .config import DATA_DIR


# ---------------------------------------------------------
# SESSION DIRECTORY MAPPING
# ---------------------------------------------------------

SESSION_LABELS = {
    "fp1": "Practice 1",
    "fp2": "Practice 2",
    "fp3": "Practice 3",
    "qualifying": "Qualifying",
    "sprint": "Sprint",
    "sprint_qualifying": "Sprint Qualifying",
    "race": "Race",
}


def pretty_label(value: str) -> str:
    """Convert a filesystem name into a human-readable label."""

    return value.replace("_", " ").title()


def get_sessions_root() -> Path:
    """Return the root directory containing all processed datasets."""

    return DATA_DIR


def list_seasons() -> list[int]:
    """Return all seasons currently available in the data directory."""

    if not DATA_DIR.exists():
        return []

    seasons = []

    for path in DATA_DIR.iterdir():

        if path.is_dir() and path.name.isdigit():
            seasons.append(int(path.name))

    return sorted(seasons)


def list_events(year: int) -> list[dict]:
    """Return all events available for a given season."""

    year_dir = DATA_DIR / str(year)

    if not year_dir.exists() or not year_dir.is_dir():
        return []

    events = []

    for path in sorted(year_dir.iterdir()):

        if not path.is_dir():
            continue

        events.append(
            {
                "id": path.name,
                "name": pretty_label(path.name),
            }
        )

    return events


def list_sessions(year: int, event: str) -> list[dict]:
    """Return all sessions available for an event."""

    event_dir = DATA_DIR / str(year) / event

    if not event_dir.exists() or not event_dir.is_dir():
        return []

    sessions = []

    for path in sorted(event_dir.iterdir()):

        if not path.is_dir():
            continue

        # A valid processed session should contain metadata and data files.
        metadata_file = path / "metadata.json"
        laps_file = path / "laps.parquet"
        telemetry_file = path / "telemetry.parquet"

        if not (
            metadata_file.exists()
            and laps_file.exists()
            and telemetry_file.exists()
        ):
            continue

        session_id = path.name

        sessions.append(
            {
                "id": session_id,
                "name": SESSION_LABELS.get(
                    session_id,
                    pretty_label(session_id),
                ),
            }
        )

    return sessions


def get_dataset_path(
    year: int,
    event: str,
    session: str,
) -> Path:
    """Return the directory containing one processed session."""

    return DATA_DIR / str(year) / event / session


def list_drivers(
    year: int,
    event: str,
    session: str,
) -> list[dict]:
    """Return the drivers available in a processed session."""

    dataset_dir = get_dataset_path(
        year=year,
        event=event,
        session=session,
    )

    drivers_file = dataset_dir / "drivers.parquet"

    if not drivers_file.exists():
        return []

    drivers = pd.read_parquet(drivers_file)

    result = []

    for _, row in drivers.iterrows():

        result.append(
            {
                "driver": row["driver"],
                "driver_number": str(row["driver_number"]),
                "team": row["team"],
            }
        )

    return result