from pathlib import Path

import numpy as np
import pandas as pd

from .datasets import get_dataset_path


# ---------------------------------------------------------
# TELEMETRY COLUMNS
# ---------------------------------------------------------

TELEMETRY_COLUMNS = [
    "driver",
    "driver_number",
    "lap_number",
    "session_time",
    "distance",
    "relative_distance",
    "speed",
    "rpm",
    "gear",
    "throttle",
    "brake",
    "drs",
    "x",
    "y",
    "z",
    "driver_ahead",
    "distance_to_driver_ahead",
    "status",
    "source",
]


# ---------------------------------------------------------
# PLAYBACK CONFIGURATION
# ---------------------------------------------------------

DEFAULT_PLAYBACK_FRAMES = 500
DEFAULT_PLAYBACK_FPS = 20


# ---------------------------------------------------------
# DATASET ACCESS
# ---------------------------------------------------------

def get_telemetry_file(
    year: int,
    event: str,
    session: str,
) -> Path:
    """Return the telemetry Parquet file for a session."""

    dataset_dir = get_dataset_path(
        year=year,
        event=event,
        session=session,
    )

    return dataset_dir / "telemetry.parquet"


# ---------------------------------------------------------
# JSON SAFETY
# ---------------------------------------------------------

def clean_telemetry_for_json(
    telemetry: pd.DataFrame,
) -> pd.DataFrame:
    """
    Replace values that are not valid JSON numbers.

    NaN and infinite values become None.
    """

    cleaned = telemetry.copy()

    cleaned = cleaned.replace(
        {
            np.nan: None,
            np.inf: None,
            -np.inf: None,
        }
    )

    return cleaned


# ---------------------------------------------------------
# TELEMETRY LOADER
# ---------------------------------------------------------

def load_telemetry(
    year: int,
    event: str,
    session: str,
    driver: str | None = None,
    lap: int | None = None,
) -> pd.DataFrame:
    """
    Load telemetry for a session.

    Optional filters:
    - driver: three-letter driver code, e.g. VER
    - lap: lap number
    """

    telemetry_file = get_telemetry_file(
        year=year,
        event=event,
        session=session,
    )

    if not telemetry_file.exists():
        raise FileNotFoundError(
            f"Telemetry dataset not found: {telemetry_file}"
        )

    filters = []

    if driver is not None:
        filters.append(
            ("driver", "==", driver.upper())
        )

    if lap is not None:
        filters.append(
            ("lap_number", "==", lap)
        )

    telemetry = pd.read_parquet(
        telemetry_file,
        columns=TELEMETRY_COLUMNS,
        filters=filters or None,
    )

    telemetry = telemetry.reset_index(drop=True)

    return clean_telemetry_for_json(
        telemetry
    )


# ---------------------------------------------------------
# DRIVER TELEMETRY
# ---------------------------------------------------------

def load_driver_telemetry(
    year: int,
    event: str,
    session: str,
    driver: str,
    lap: int | None = None,
) -> pd.DataFrame:
    """Load telemetry for one driver."""

    return load_telemetry(
        year=year,
        event=event,
        session=session,
        driver=driver,
        lap=lap,
    )


# ---------------------------------------------------------
# PLAYBACK INTERPOLATION
# ---------------------------------------------------------

NUMERIC_PLAYBACK_COLUMNS = [
    "session_time",
    "distance",
    "relative_distance",
    "speed",
    "rpm",
    "gear",
    "throttle",
    "x",
    "y",
    "z",
    "distance_to_driver_ahead",
]


STEP_COLUMNS = [
    "brake",
    "drs",
]


CATEGORICAL_COLUMNS = [
    "driver_ahead",
    "status",
    "source",
]


def _safe_float_array(
    values: pd.Series,
) -> np.ndarray:
    """Convert a numeric series to finite float values."""

    array = pd.to_numeric(
        values,
        errors="coerce",
    ).to_numpy(
        dtype=float
    )

    if np.all(np.isnan(array)):
        return np.zeros(
            len(array),
            dtype=float,
        )

    valid = ~np.isnan(array)

    if not np.all(valid):
        indices = np.arange(len(array))

        array[~valid] = np.interp(
            indices[~valid],
            indices[valid],
            array[valid],
        )

    return array


def _interpolate_numeric(
    dataframe: pd.DataFrame,
    column: str,
    target_progress: np.ndarray,
) -> np.ndarray:
    """Interpolate a numeric telemetry column."""

    source_progress = _safe_float_array(
        dataframe["relative_distance"]
    )

    values = _safe_float_array(
        dataframe[column]
    )

    # Ensure the interpolation axis is monotonically increasing.
    order = np.argsort(
        source_progress
    )

    source_progress = source_progress[order]
    values = values[order]

    unique_progress, unique_indices = np.unique(
        source_progress,
        return_index=True,
    )

    values = values[unique_indices]

    if len(unique_progress) == 1:
        return np.full(
            len(target_progress),
            values[0],
        )

    return np.interp(
        target_progress,
        unique_progress,
        values,
    )


def _nearest_step_values(
    dataframe: pd.DataFrame,
    column: str,
    target_progress: np.ndarray,
) -> np.ndarray:
    """Sample boolean/integer state values using nearest points."""

    source_progress = _safe_float_array(
        dataframe["relative_distance"]
    )

    values = dataframe[column].tolist()

    output = []

    for progress in target_progress:

        index = int(
            np.argmin(
                np.abs(
                    source_progress - progress
                )
            )
        )

        value = values[index]

        if pd.isna(value):
            value = None

        output.append(value)

    return np.array(
        output,
        dtype=object,
    )


def _nearest_categorical_values(
    dataframe: pd.DataFrame,
    column: str,
    target_progress: np.ndarray,
) -> list:
    """Sample categorical values using nearest points."""

    source_progress = _safe_float_array(
        dataframe["relative_distance"]
    )

    values = dataframe[column].tolist()

    output = []

    for progress in target_progress:

        index = int(
            np.argmin(
                np.abs(
                    source_progress - progress
                )
            )
        )

        value = values[index]

        if pd.isna(value):
            value = None

        output.append(value)

    return output


def resample_driver_lap(
    telemetry: pd.DataFrame,
    frames: int = DEFAULT_PLAYBACK_FRAMES,
) -> list[dict]:
    """
    Resample one driver's lap into a fixed number of playback frames.

    The stored dataset remains at original resolution.
    """

    if telemetry.empty:
        return []

    telemetry = telemetry.copy()

    telemetry = telemetry.sort_values(
        "relative_distance"
    ).reset_index(
        drop=True
    )

    target_progress = np.linspace(
        0.0,
        1.0,
        frames,
    )

    result = []

    for frame_index, progress in enumerate(
        target_progress
    ):

        frame = {
            "frame": frame_index,
            "progress": float(progress),
        }

        # Numeric channels
        for column in NUMERIC_PLAYBACK_COLUMNS:

            values = _interpolate_numeric(
                telemetry,
                column,
                np.array([progress]),
            )

            value = float(values[0])

            if column in {
                "gear",
            }:
                value = int(
                    round(value)
                )

            frame[column] = value

        # Boolean / state channels
        for column in STEP_COLUMNS:

            value = _nearest_step_values(
                telemetry,
                column,
                np.array([progress]),
            )[0]

            frame[column] = value

        # Categorical channels
        for column in CATEGORICAL_COLUMNS:

            value = _nearest_categorical_values(
                telemetry,
                column,
                np.array([progress]),
            )[0]

            frame[column] = value

        frame["driver"] = telemetry.iloc[0][
            "driver"
        ]

        frame["driver_number"] = str(
            telemetry.iloc[0][
                "driver_number"
            ]
        )

        frame["lap_number"] = int(
            telemetry.iloc[0][
                "lap_number"
            ]
        )

        result.append(frame)

    return result


# ---------------------------------------------------------
# MULTI-DRIVER PLAYBACK
# ---------------------------------------------------------

def build_playback_frames(
    year: int,
    event: str,
    session: str,
    lap: int,
    drivers: list[str],
    frames: int = DEFAULT_PLAYBACK_FRAMES,
) -> list[dict]:
    """
    Build synchronized playback frames for multiple drivers.

    Each driver is independently resampled onto the same
    relative-distance timeline.
    """

    if not drivers:
        return []

    driver_frames = {}

    for driver in drivers:

        telemetry = load_driver_telemetry(
            year=year,
            event=event,
            session=session,
            driver=driver,
            lap=lap,
        )

        if telemetry.empty:
            continue

        driver_frames[
            driver.upper()
        ] = resample_driver_lap(
            telemetry,
            frames=frames,
        )

    if not driver_frames:
        return []

    playback = []

    for frame_index in range(frames):

        frame_drivers = []

        for driver, frames_data in driver_frames.items():

            if frame_index >= len(
                frames_data
            ):
                continue

            frame_drivers.append(
                frames_data[
                    frame_index
                ]
            )

        playback.append(
            {
                "frame": frame_index,
                "progress": (
                    frame_index
                    / (frames - 1)
                    if frames > 1
                    else 0.0
                ),
                "drivers": frame_drivers,
            }
        )

    return playback