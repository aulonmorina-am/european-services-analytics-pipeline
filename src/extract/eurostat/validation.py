from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .models import DatasetConfig


class ValidationError(ValueError):
    """Raised when a downloaded dataset fails validation."""


class EmptyPartitionError(ValidationError):
    """Raised when a valid partition response contains no data rows."""


@dataclass(frozen=True)
class ValidationResult:
    checksum: str
    byte_count: int
    row_count: int
    columns: tuple[str, ...]


def validate_csv(path: Path, dataset: DatasetConfig) -> ValidationResult:
    checksum = hashlib.sha256()
    byte_count = 0

    with path.open("rb") as binary_file:
        for chunk in iter(lambda: binary_file.read(1024 * 1024), b""):
            checksum.update(chunk)
            byte_count += len(chunk)

    if byte_count == 0:
        raise ValidationError(f"{dataset.code} response is empty.")

    with path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        columns = tuple(reader.fieldnames or ())
        missing = set(dataset.required_columns) - set(columns)
        if missing:
            raise ValidationError(
                f"{dataset.code} is missing required columns: {', '.join(sorted(missing))}"
            )

        row_count = 0
        periods: set[str] = set()
        has_conf_status = "CONF_STATUS" in columns
        for row in reader:
            row_count += 1
            period = row.get("TIME_PERIOD")
            if period:
                periods.add(period)
            value = row.get("OBS_VALUE")
            if value not in (None, ""):
                try:
                    float(value)
                except ValueError as exc:
                    raise ValidationError(
                        f"{dataset.code} contains a non-numeric OBS_VALUE: {value!r}"
                    ) from exc
            if has_conf_status:
                _validate_flag_consistency(dataset, row, value)

        if row_count == 0:
            raise EmptyPartitionError(f"{dataset.code} contains no data rows.")
        _validate_periods(dataset, periods)

    return ValidationResult(
        checksum=checksum.hexdigest(),
        byte_count=byte_count,
        row_count=row_count,
        columns=columns,
    )


def _validate_flag_consistency(
    dataset: DatasetConfig, row: dict[str, str], value: str | None
) -> None:
    """Cross-check OBS_VALUE against CONF_STATUS when the columns are present.

    Eurostat suppresses confidential values: an empty OBS_VALUE must carry a
    CONF_STATUS reason ('C' = confidential), and a row marked 'C' must not carry
    a value.
    """
    conf_status = (row.get("CONF_STATUS") or "").strip()
    is_empty = value in (None, "")
    if is_empty and not conf_status:
        raise ValidationError(
            f"{dataset.code} has an empty OBS_VALUE without CONF_STATUS "
            f"(period={row.get('TIME_PERIOD')!r})."
        )
    if conf_status == "C" and not is_empty:
        raise ValidationError(
            f"{dataset.code} marks CONF_STATUS=C but OBS_VALUE is present: {value!r}."
        )


def _validate_periods(dataset: DatasetConfig, periods: set[str]) -> None:
    if not periods or not dataset.start_period:
        return
    start_year = int(dataset.start_period[:4])
    end_year = int(dataset.end_period[:4]) if dataset.end_period else None
    years = {int(period[:4]) for period in periods if period[:4].isdigit()}
    if any(year < start_year for year in years):
        raise ValidationError(f"{dataset.code} contains data before {dataset.start_period}.")
    if end_year is not None and any(year > end_year for year in years):
        raise ValidationError(f"{dataset.code} contains data after {dataset.end_period}.")
