from pathlib import Path

import pandas as pd

from .config import DATA_DIR


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
    return value.replace("_", " ").title()


def get_sessions_root() -> Path:
    return DATA_DIR


def list_seasons() -> list[int]:
    if not DATA_DIR.exists():
        return []

    seasons = []

    for path in DATA_DIR.iterdir():
        if path.is_dir() and path.name.isdigit():
            seasons.append(int(path.name))

    return sorted(seasons)


def list_events(year: int) -> list[dict]:
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


def list_sessions(
    year: int,
    event: str,
) -> list[dict]:
    event_dir = DATA_DIR / str(year) / event

    if not event_dir.exists() or not event_dir.is_dir():
        return []

    sessions = []

    for path in sorted(event_dir.iterdir()):
        if not path.is_dir():
            continue

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
    return (
        DATA_DIR
        / str(year)
        / event
        / session
    )


def list_drivers(
    year: int,
    event: str,
    session: str,
) -> list[dict]:
    dataset_dir = get_dataset_path(
        year=year,
        event=event,
        session=session,
    )

    drivers_file = dataset_dir / "drivers.parquet"

    if not drivers_file.exists():
        return []

    drivers = pd.read_parquet(
        drivers_file
    )

    result = []

    for _, row in drivers.iterrows():
        result.append(
            {
                "driver": row["driver"],
                "driver_number": str(
                    row["driver_number"]
                ),
                "team": row["team"],
            }
        )

    return result


# =========================================================
# LAP AVAILABILITY
# =========================================================

def get_lap_availability(
    year: int,
    event: str,
    session: str,
    drivers: list[str] | None = None,
) -> dict:
    """
    Return lap availability for a session.

    When drivers are supplied, common_laps contains only
    laps that exist for every requested driver.

    We intentionally keep inaccurate laps here. The
    is_accurate flag describes lap quality; it does not
    mean the lap should be hidden from the user.
    """

    dataset_dir = get_dataset_path(
        year=year,
        event=event,
        session=session,
    )

    laps_file = dataset_dir / "laps.parquet"

    if not laps_file.exists():
        return {
            "all_laps": [],
            "common_laps": [],
            "driver_laps": {},
        }

    laps = pd.read_parquet(
        laps_file,
        columns=[
            "driver",
            "lap_number",
        ],
    )

    if laps.empty:
        return {
            "all_laps": [],
            "common_laps": [],
            "driver_laps": {},
        }

    laps = laps.copy()

    laps["driver"] = (
        laps["driver"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    laps["lap_number"] = pd.to_numeric(
        laps["lap_number"],
        errors="coerce",
    )

    laps = laps.dropna(
        subset=["lap_number"]
    )

    laps["lap_number"] = (
        laps["lap_number"]
        .astype(int)
    )

    driver_laps = {}

    for driver, driver_rows in laps.groupby(
        "driver"
    ):
        driver_laps[driver] = sorted(
            driver_rows["lap_number"]
            .unique()
            .tolist()
        )

    all_laps = sorted(
        laps["lap_number"]
        .unique()
        .tolist()
    )

    if drivers:
        normalized_drivers = [
            str(driver)
            .strip()
            .upper()
            for driver in drivers
            if str(driver).strip()
        ]

        selected_sets = [
            set(
                driver_laps.get(
                    driver,
                    [],
                )
            )
            for driver in normalized_drivers
        ]

        if selected_sets:
            common_laps = sorted(
                set.intersection(
                    *selected_sets
                )
            )
        else:
            common_laps = []

        selected_driver_laps = {
            driver: driver_laps.get(
                driver,
                [],
            )
            for driver in normalized_drivers
        }

    else:
        normalized_drivers = []
        common_laps = all_laps
        selected_driver_laps = driver_laps

    return {
        "all_laps": all_laps,
        "common_laps": common_laps,
        "driver_laps": selected_driver_laps,
    }