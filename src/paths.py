"""Project-wide path constants.

All paths are anchored to the repository root so the pipeline behaves the same
regardless of the current working directory.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / 'config'
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'output'
STATE_DIR = PROJECT_ROOT / 'state'
TEMPLATES_DIR = PROJECT_ROOT / 'templates'
EXAMPLES_DIR = PROJECT_ROOT / 'examples'


def ensure_runtime_dirs() -> None:
    """Create the directories the pipeline writes to."""
    for directory in (RAW_DATA_DIR, PROCESSED_DATA_DIR, OUTPUT_DIR, STATE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
