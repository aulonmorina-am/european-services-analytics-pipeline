from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .extractor import run


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
            },
            sort_keys=True,
        )


def main() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])

    datasets = _configured_datasets()
    run(
        config_path=Path(os.getenv("EUROSTAT_CONFIG_PATH", "config/datasets.yaml")),
        datasets=datasets,
        run_year=_optional_run_year(),
    )


def _configured_datasets() -> tuple[str, ...] | None:
    value = os.getenv("EUROSTAT_DATASETS", "").strip()
    if not value:
        return None
    return tuple(dataset.strip() for dataset in value.split(",") if dataset.strip())


def _optional_run_year() -> int | None:
    value = os.getenv("EUROSTAT_RUN_YEAR", "").strip()
    return int(value) if value else None


if __name__ == "__main__":
    main()
