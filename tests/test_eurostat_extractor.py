from pathlib import Path

import pytest

from extract.eurostat.client import build_data_url
from extract.eurostat.config import load_extractor_config
from extract.eurostat.extractor import _configured_years
from extract.eurostat.validation import EmptyPartitionError, ValidationError, validate_csv

ROOT = Path(__file__).parents[1]


def test_dataset_configuration_contains_required_sources() -> None:
    config = load_extractor_config(ROOT / "config" / "datasets.yaml")

    assert set(config.datasets) == {
        "bop_its6_det",
        "ext_stec01",
        "ext_stec02",
        "ext_stec03",
    }
    assert config.datasets["bop_its6_det"].start_period == "2022"
    assert config.datasets["bop_its6_det"].end_period == "2024"
    assert config.datasets["ext_stec01"].start_period == "2022"
    assert config.datasets["ext_stec01"].end_period == "2024"
    assert config.datasets["ext_stec02"].end_period == "2024"
    assert config.datasets["ext_stec03"].end_period == "2024"
    assert _configured_years(config.datasets["bop_its6_det"]) == (2022, 2023, 2024)


def test_build_data_url_uses_sdmx_csv_and_periods() -> None:
    config = load_extractor_config(ROOT / "config" / "datasets.yaml")

    url = build_data_url(config.datasets["bop_its6_det"], partition_value="DE")

    assert "bop_its6_det" in url
    assert "/bop_its6_det/.....DE?" in url
    assert "format=SDMX-CSV" in url
    assert "detail=dataonly" in url
    assert "startPeriod=2022" in url
    assert "endPeriod=2024" in url


def test_validate_csv_checks_columns_values_and_periods(tmp_path: Path) -> None:
    config = load_extractor_config(ROOT / "config" / "datasets.yaml")
    dataset = config.datasets["bop_its6_det"]
    path = tmp_path / "bop_its6_det.csv"
    path.write_text(
        "freq,currency,bop_item,stk_flow,partner,geo,TIME_PERIOD,OBS_VALUE\n"
        "A,MIO_EUR,SERV,EXP,US,DE,2023,123.4\n",
        encoding="utf-8",
    )

    result = validate_csv(path, dataset)

    assert result.row_count == 1
    assert result.byte_count == path.stat().st_size
    assert len(result.checksum) == 64


def test_validate_csv_rejects_invalid_values(tmp_path: Path) -> None:
    config = load_extractor_config(ROOT / "config" / "datasets.yaml")
    dataset = config.datasets["bop_its6_det"]
    path = tmp_path / "bop_its6_det.csv"
    path.write_text(
        "freq,currency,bop_item,stk_flow,partner,geo,TIME_PERIOD,OBS_VALUE\n"
        "A,MIO_EUR,SERV,EXP,US,DE,2023,not-a-number\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="non-numeric OBS_VALUE"):
        validate_csv(path, dataset)


def test_validate_csv_identifies_empty_partition(tmp_path: Path) -> None:
    config = load_extractor_config(ROOT / "config" / "datasets.yaml")
    dataset = config.datasets["bop_its6_det"]
    path = tmp_path / "bop_its6_det.csv"
    path.write_text(
        "freq,currency,bop_item,stk_flow,partner,geo,TIME_PERIOD,OBS_VALUE\n",
        encoding="utf-8",
    )

    with pytest.raises(EmptyPartitionError, match="contains no data rows"):
        validate_csv(path, dataset)
