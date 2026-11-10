from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import DatasetConfig
from .validation import ValidationResult


def write_manifest(
    path: Path,
    *,
    dataset: DatasetConfig,
    source_url: str,
    validation: ValidationResult,
) -> None:
    manifest = {
        "dataset": dataset.code,
        "description": dataset.description,
        "source_url": source_url,
        "format": dataset.format,
        "start_period": dataset.start_period,
        "end_period": dataset.end_period,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        **asdict(validation),
    }
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
