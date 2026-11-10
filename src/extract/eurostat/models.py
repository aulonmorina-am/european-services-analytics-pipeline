from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetConfig:
    code: str
    description: str
    endpoint: str
    format: str = "TSV"
    start_period: str | None = None
    end_period: str | None = None
    filters: dict[str, str] = field(default_factory=dict)
    required_columns: tuple[str, ...] = ()
    key_dimensions: tuple[str, ...] = ()
    partition_dimension: str | None = None
    partition_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractorConfig:
    datasets: dict[str, DatasetConfig]


@dataclass(frozen=True)
class AdlsConfig:
    account_name: str
    filesystem: str
    root_path: str = "raw/eurostat"


@dataclass(frozen=True)
class ExtractionRequest:
    dataset: DatasetConfig
    run_year: int
    partition_value: str | None = None
