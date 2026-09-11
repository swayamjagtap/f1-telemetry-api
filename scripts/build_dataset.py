from pathlib import Path
import json
import sys

import pandas as pd


# ---------------------------------------------------------
# PROJECT IMPORTS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.sessions import get_session_directory  # noqa: E402
from scripts.download_session import load_session  # noqa: E402


# ---------------------------------------------------------
# DATASET CONFIGURATION
# ---------------------------------------------------------

YEAR = 2025
EVENT = "Abu Dhabi"
SESSION_TYPE = "Q"

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def format_timedelta(value):
    """
    Convert a pandas Timedelta into seconds.

    Missing values become None.
    """

    if pd.isna(value):
        return None

    return value.total_seconds()


# ---------------------------------------------------------
# BUILD DRIVERS DATASET
# ---------------------------------------------------------

def build_drivers_dataset(session) -> pd.DataFrame:
    """Create the standardized driver table."""

    rows = []

    for driver_number in session.drivers:

        driver_laps = session.laps.pick_drivers(driver_number)

        if driver_laps.empty:
            continue

        first_lap = driver_laps.iloc[0]

        rows.append(
            {
                "driver": first_lap["Driver"],
                "driver_number": str(first_lap["DriverNumber"]),
                "team": first_lap["Team"],
            }
        )

    drivers = pd.DataFrame(rows)

    if not drivers.empty:
        drivers = drivers.drop_duplicates(
            subset=["driver"]
        ).reset_index(drop=True)

    return drivers


# ---------------------------------------------------------
# BUILD LAPS DATASET
# ---------------------------------------------------------

def build_laps_dataset(session) -> pd.DataFrame:
    """Create the standardized lap-level dataset."""

    laps = session.laps.copy()

    result = pd.DataFrame(
        {
            "driver": laps["Driver"],
            "driver_number": laps["DriverNumber"].astype(str),
            "lap_number": laps["LapNumber"],
            "lap_time": laps["LapTime"].apply(format_timedelta),
            "sector_1_time": laps["Sector1Time"].apply(format_timedelta),
            "sector_2_time": laps["Sector2Time"].apply(format_timedelta),
            "sector_3_time": laps["Sector3Time"].apply(format_timedelta),
            "position": laps["Position"],
            "compound": laps["Compound"],
            "tyre_life": laps["TyreLife"],
            "fresh_tyre": laps["FreshTyre"],
            "is_personal_best": laps["IsPersonalBest"],
            "is_accurate": laps["IsAccurate"],
            "deleted": laps["Deleted"],
            "deleted_reason": laps["DeletedReason"],
            "track_status": laps["TrackStatus"],
        }
    )

    return result.reset_index(drop=True)


# ---------------------------------------------------------
# BUILD TELEMETRY DATASET
# ---------------------------------------------------------

def build_telemetry_dataset(session) -> pd.DataFrame:
    """
    Build the canonical high-frequency telemetry dataset.

    One row represents one telemetry sample for one driver/lap.
    """

    telemetry_frames = []

    for driver in session.drivers:

        driver_laps = session.laps.pick_drivers(driver)

        for _, lap in driver_laps.iterlaps():

            try:
                telemetry = lap.get_telemetry()

                if telemetry.empty:
                    continue

            except Exception:
                continue

            frame = pd.DataFrame(
                {
                    "driver": lap["Driver"],
                    "driver_number": str(lap["DriverNumber"]),
                    "lap_number": lap["LapNumber"],

                    "session_time": telemetry["SessionTime"].apply(
                        format_timedelta
                    ),
                    "distance": telemetry["Distance"],
                    "relative_distance": telemetry["RelativeDistance"],

                    "speed": telemetry["Speed"],
                    "rpm": telemetry["RPM"],
                    "gear": telemetry["nGear"],
                    "throttle": telemetry["Throttle"],
                    "brake": telemetry["Brake"],
                    "drs": telemetry["DRS"],

                    "x": telemetry["X"],
                    "y": telemetry["Y"],
                    "z": telemetry["Z"],

                    "driver_ahead": telemetry["DriverAhead"],
                    "distance_to_driver_ahead": telemetry[
                        "DistanceToDriverAhead"
                    ],
                    "status": telemetry["Status"],
                    "source": telemetry["Source"],
                }
            )

            telemetry_frames.append(frame)

    if not telemetry_frames:
        return pd.DataFrame()

    return pd.concat(
        telemetry_frames,
        ignore_index=True,
    )


# ---------------------------------------------------------
# BUILD METADATA
# ---------------------------------------------------------

def build_metadata(session) -> dict:
    """Create dataset metadata."""

    return {
        "schema_version": SCHEMA_VERSION,
        "year": YEAR,
        "event": EVENT,
        "session": session.name,
        "session_code": SESSION_TYPE,
        "driver_count": len(session.drivers),
        "lap_count": len(session.laps),
    }


# ---------------------------------------------------------
# WRITE DATASET
# ---------------------------------------------------------

def write_dataset(output_dir: Path, session) -> None:
    """Build and write all standardized dataset files."""

    print()
    print("=" * 60)
    print("BUILDING DATASET")
    print("=" * 60)

    # Drivers
    print("\nBuilding drivers dataset...")
    drivers = build_drivers_dataset(session)

    drivers_path = output_dir / "drivers.parquet"
    drivers.to_parquet(
        drivers_path,
        index=False,
    )

    print(
        f"Drivers: {len(drivers):,} rows"
    )

    # Laps
    print("\nBuilding laps dataset...")
    laps = build_laps_dataset(session)

    laps_path = output_dir / "laps.parquet"
    laps.to_parquet(
        laps_path,
        index=False,
    )

    print(
        f"Laps: {len(laps):,} rows"
    )

    # Telemetry
    print("\nBuilding telemetry dataset...")
    telemetry = build_telemetry_dataset(session)

    telemetry_path = output_dir / "telemetry.parquet"
    telemetry.to_parquet(
        telemetry_path,
        index=False,
    )

    print(
        f"Telemetry: {len(telemetry):,} rows"
    )

    # Metadata
    print("\nBuilding metadata...")

    metadata = build_metadata(session)

    metadata_path = output_dir / "metadata.json"

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=4,
        )

    print("Metadata written.")

    print("\n" + "=" * 60)
    print("DATASET BUILD COMPLETE")
    print("=" * 60)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    session = load_session(
        year=YEAR,
        event=EVENT,
        session_type=SESSION_TYPE,
    )

    output_dir = get_session_directory(
        year=YEAR,
        event_name=EVENT,
        session_type=SESSION_TYPE,
    )

    write_dataset(
        output_dir=output_dir,
        session=session,
    )


if __name__ == "__main__":
    main()