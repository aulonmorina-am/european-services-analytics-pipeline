from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .models import AdlsConfig, DatasetConfig, ExtractorConfig


class ConfigurationError(ValueError):
    """Raised when extractor configuration is missing or invalid."""


def load_extractor_config(path: Path) -> ExtractorConfig:
    try:
        raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in configuration file: {path}") from exc

    if not isinstance(raw_config, dict) or not isinstance(raw_config.get("datasets"), dict):
        raise ConfigurationError("Configuration must contain a 'datasets' mapping.")

    datasets: dict[str, DatasetConfig] = {}
    for code, raw_dataset in raw_config["datasets"].items():
        if not isinstance(code, str) or not isinstance(raw_dataset, dict):
            raise ConfigurationError("Each dataset must be a named mapping.")
        datasets[code] = _parse_dataset(code, raw_dataset)

    if not datasets:
        raise ConfigurationError("At least one dataset must be configured.")
    return ExtractorConfig(datasets=datasets)


def get_dataset(config: ExtractorConfig, code: str) -> DatasetConfig:
    try:
        return config.datasets[code]
    except KeyError as exc:
        available = ", ".join(sorted(config.datasets))
        raise ConfigurationError(
            f"Unknown dataset '{code}'. Available datasets: {available}"
        ) from exc


def load_adls_config() -> AdlsConfig:
    account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    filesystem = os.getenv("AZURE_STORAGE_FILESYSTEM")
    if not account_name or not filesystem:
        raise ConfigurationError(
            "AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_FILESYSTEM must be set."
        )

    return AdlsConfig(
        account_name=account_name,
        filesystem=filesystem,
        root_path=os.getenv("AZURE_STORAGE_ROOT_PATH", "raw/eurostat"),
    )


def _parse_dataset(code: str, raw_dataset: dict[str, Any]) -> DatasetConfig:
    endpoint = raw_dataset.get("endpoint")
    description = raw_dataset.get("description", "")
    if not isinstance(endpoint, str) or not endpoint:
        raise ConfigurationError(f"Dataset '{code}' must define a non-empty endpoint.")
    if not isinstance(description, str):
        raise ConfigurationError(f"Dataset '{code}' has an invalid description.")

    filters = raw_dataset.get("filters", {})
    required_columns = raw_dataset.get("required_columns", [])
    key_dimensions = raw_dataset.get("key_dimensions", [])
    partition_dimension = raw_dataset.get("partition_dimension")
    partition_values = raw_dataset.get("partition_values", [])
    if not isinstance(filters, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in filters.items()
    ):
        raise ConfigurationError(f"Dataset '{code}' filters must be a string mapping.")
    if not isinstance(required_columns, list) or not all(
        isinstance(column, str) for column in required_columns
    ):
        raise ConfigurationError(f"Dataset '{code}' required_columns must be a list of strings.")
    if not isinstance(key_dimensions, list) or not all(
        isinstance(dimension, str) for dimension in key_dimensions
    ):
        raise ConfigurationError(f"Dataset '{code}' key_dimensions must be a list of strings.")
    if partition_dimension is not None and (
        not isinstance(partition_dimension, str) or partition_dimension not in key_dimensions
    ):
        raise ConfigurationError(
            f"Dataset '{code}' partition_dimension must be present in key_dimensions."
        )
    if not isinstance(partition_values, list) or not all(
        isinstance(value, str) for value in partition_values
    ):
        raise ConfigurationError(f"Dataset '{code}' partition_values must be a list of strings.")

    return DatasetConfig(
        code=code,
        description=description,
        endpoint=endpoint,
        format=_string_value(raw_dataset, "format", "TSV"),
        start_period=_optional_string(raw_dataset, "start_period"),
        end_period=_optional_string(raw_dataset, "end_period"),
        filters=dict(filters),
        required_columns=tuple(required_columns),
        key_dimensions=tuple(key_dimensions),
        partition_dimension=partition_dimension,
        partition_values=tuple(partition_values),
    )


def _string_value(values: dict[str, Any], key: str, default: str) -> str:
    value = values.get(key, default)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"Configuration value '{key}' must be a non-empty string.")
    return value


def _optional_string(values: dict[str, Any], key: str) -> str | None:
    value = values.get(key)
    if value is not None and (not isinstance(value, str) or not value):
        raise ConfigurationError(f"Configuration value '{key}' must be a non-empty string.")
    return value
