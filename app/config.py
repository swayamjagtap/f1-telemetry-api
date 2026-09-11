from pathlib import Path


# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Local FastF1 cache
CACHE_DIR = BASE_DIR / "cache"

# Processed dataset storage
DATA_DIR = BASE_DIR / "data"

# Default dataset for the first version
DEFAULT_YEAR = 2025
DEFAULT_EVENT = "Abu Dhabi"
DEFAULT_SESSION = "Q"