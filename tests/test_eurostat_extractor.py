from pathlib import Path

import pytest

from extract.eurostat.adls import AdlsWriter
from extract.eurostat.client import build_data_url
from extract.eurostat.config import (
    ConfigurationError,
    get_dataset,
    load_extractor_config,
)
from extract.eurostat.extractor import _configured_years
from extract.eurostat.models import AdlsConfig, DatasetConfig
from extract.eurostat.validation import EmptyPartitionError, ValidationError, validate_csv

ROOT = Path(__file__).parents[1]
CONFIG_PATH = ROOT / "config" / "datasets.yaml"

# Header as returned by the Eurostat SDMX-CSV API with detail=full
# (OBS_FLAG / CONF_STATUS are only present when detail is not "dataonly").
FULL_HEADER = (
    "DATAFLOW,LAST UPDATE,freq,currency,bop_item,stk_flow,partner,geo,"
    "TIME_PERIOD,OBS_VALUE,OBS_FLAG,CONF_STATUS"
)


def _dataset(code: str = "bop_its6_det") -> DatasetConfig:
    return load_extractor_config(CONFIG_PATH).datasets[code]


def _write_csv(
    tmp_path: Path, body: str, *, header: str = FULL_HEADER, encoding: str = "utf-8"
) -> Path:
    path = tmp_path / "data.csv"
    path.write_text(header + "\n" + body, encoding=encoding)
    return path


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def test_dataset_configuration_contains_required_sources() -> None:
    config = load_extractor_config(CONFIG_PATH)

    assert set(config.datasets) == {
        "bop_its6_det",
        "ext_stec01",
        "ext_stec02",
        "ext_stec03",
    }
    for dataset in config.datasets.values():
        assert dataset.start_period == "2022"
        assert dataset.end_period == "2024"
        # flag columns must be required so a detail=dataonly response fails loudly
        assert "OBS_FLAG" in dataset.required_columns
        assert "CONF_STATUS" in dataset.required_columns
        assert "OBS_VALUE" in dataset.required_columns
    assert _configured_years(config.datasets["bop_its6_det"]) == (2022, 2023, 2024)


def test_get_dataset_unknown_code_lists_available() -> None:
    config = load_extractor_config(CONFIG_PATH)

    with pytest.raises(ConfigurationError, match="Unknown dataset 'nope'.*bop_its6_det"):
        get_dataset(config, "nope")


def test_config_rejects_partition_dimension_outside_key_dimensions(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "datasets:\n"
        "  demo:\n"
        "    endpoint: https://example.test/data\n"
        "    key_dimensions: [freq]\n"
        "    partition_dimension: geo\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="partition_dimension must be present"):
        load_extractor_config(bad)


def test_config_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_extractor_config(tmp_path / "absent.yaml")


def test_configured_years_rejects_reversed_or_missing_range() -> None:
    dataset = _dataset()
    reversed_ds = DatasetConfig(
        code="x", description="", endpoint="https://e.test", start_period="2024", end_period="2022"
    )
    with pytest.raises(ValueError, match="Invalid period range"):
        _configured_years(reversed_ds)

    no_periods = DatasetConfig(code="x", description="", endpoint="https://e.test")
    with pytest.raises(ValueError, match="requires start_period and end_period"):
        _configured_years(no_periods)
    assert dataset is not None


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------


def test_build_data_url_uses_sdmx_csv_full_detail_and_periods() -> None:
    url = build_data_url(_dataset(), partition_value="DE")

    assert "/bop_its6_det/" in url
    assert url.split("?")[0].endswith("/.....DE")  # geo is the last key dimension
    assert "format=SDMX-CSV" in url
    assert "detail=full" in url  # dataonly would strip OBS_FLAG/CONF_STATUS
    assert "startPeriod=2022" in url
    assert "endPeriod=2024" in url


def test_build_data_url_without_partition_keeps_wildcard_key() -> None:
    url = build_data_url(_dataset())

    assert url.split("?")[0].endswith("/.....")  # all six key dimensions wildcarded
    assert "detail=full" in url


def test_build_data_url_quotes_partition_values_with_special_characters() -> None:
    dataset = DatasetConfig(
        code="demo",
        description="",
        endpoint="https://example.test/data/",
        format="SDMX-CSV",
        key_dimensions=("freq", "geo"),
        partition_dimension="geo",
    )

    url = build_data_url(dataset, partition_value="NO/2")

    assert "/demo/.NO%2F2?" in url
    assert url.startswith("https://example.test/data/demo/")  # endpoint slash normalised


def test_build_data_url_applies_filters_as_query_params() -> None:
    dataset = DatasetConfig(
        code="demo",
        description="",
        endpoint="https://example.test/data",
        format="SDMX-CSV",
        filters={"freq": "A"},
        key_dimensions=("freq", "geo"),
    )

    url = build_data_url(dataset)

    assert "freq=A" in url
    # filter value also lands in the key path for the filtered dimension
    assert "/demo/A.?" in url


# ---------------------------------------------------------------------------
# CSV validation
# ---------------------------------------------------------------------------


def test_validate_csv_accepts_full_header_with_flags_and_suppressed_rows(tmp_path: Path) -> None:
    path = _write_csv(
        tmp_path,
        "ESTAT:BOP_ITS6_DET(1.0),16/04/26 23:00:00,A,MIO_EUR,SG,CRE,US,DE,2023,123.4,,\n"
        "ESTAT:BOP_ITS6_DET(1.0),16/04/26 23:00:00,A,MIO_EUR,SC33,BAL,ASI_G,DE,2022,,,C\n"
        "ESTAT:BOP_ITS6_DET(1.0),16/04/26 23:00:00,A,MIO_EUR,SG,DEB,US,DE,2024,-5.5,u,\n",
    )

    result = validate_csv(path, _dataset())

    assert result.row_count == 3  # suppressed (empty OBS_VALUE) rows still count
    assert result.byte_count == path.stat().st_size
    assert len(result.checksum) == 64
    assert "OBS_FLAG" in result.columns
    assert "CONF_STATUS" in result.columns


def test_validate_csv_handles_bom_and_crlf(tmp_path: Path) -> None:
    path = tmp_path / "bom.csv"
    body = FULL_HEADER + "\r\n" + "x,y,A,MIO_EUR,SG,CRE,US,DE,2023,1.5,,\r\n"
    path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))

    result = validate_csv(path, _dataset())

    assert result.columns[0] == "DATAFLOW"  # BOM must not leak into the first column name
    assert result.row_count == 1


def test_validate_csv_rejects_missing_flag_columns(tmp_path: Path) -> None:
    # a detail=dataonly response has no OBS_FLAG/CONF_STATUS and must fail loudly
    old_header = (
        "DATAFLOW,LAST UPDATE,freq,currency,bop_item,stk_flow,partner,geo,TIME_PERIOD,OBS_VALUE"
    )
    path = _write_csv(
        tmp_path,
        "x,y,A,MIO_EUR,SG,CRE,US,DE,2023,1.5\n",
        header=old_header,
    )

    with pytest.raises(ValidationError, match="missing required columns: CONF_STATUS, OBS_FLAG"):
        validate_csv(path, _dataset())


def test_validate_csv_rejects_non_numeric_obs_value(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, "x,y,A,MIO_EUR,SG,CRE,US,DE,2023,not-a-number,,\n")

    with pytest.raises(ValidationError, match="non-numeric OBS_VALUE"):
        validate_csv(path, _dataset())


def test_validate_csv_rejects_empty_response(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_bytes(b"")

    with pytest.raises(ValidationError, match="response is empty"):
        validate_csv(path, _dataset())


def test_validate_csv_identifies_empty_partition(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, "")

    with pytest.raises(EmptyPartitionError, match="contains no data rows"):
        validate_csv(path, _dataset())


def test_validate_csv_accepts_empty_obs_value_without_conf_status(tmp_path: Path) -> None:
    # ext_stec01 legitimately has suppressed rows with both flag columns empty
    path = _write_csv(tmp_path, "x,y,A,MIO_EUR,SG,CRE,US,DE,2023,,,\n")

    result = validate_csv(path, _dataset())

    assert result.row_count == 1


def test_validate_csv_rejects_confidential_row_with_value(tmp_path: Path) -> None:
    path = _write_csv(tmp_path, "x,y,A,MIO_EUR,SG,CRE,US,DE,2023,99.9,,C\n")

    with pytest.raises(ValidationError, match="CONF_STATUS=C but OBS_VALUE is present"):
        validate_csv(path, _dataset())


def test_validate_csv_rejects_periods_outside_configured_range(tmp_path: Path) -> None:
    before = _write_csv(tmp_path, "x,y,A,MIO_EUR,SG,CRE,US,DE,2021,1.5,,\n")
    with pytest.raises(ValidationError, match="before 2022"):
        validate_csv(before, _dataset())

    after = _write_csv(tmp_path, "x,y,A,MIO_EUR,SG,CRE,US,DE,2025,1.5,,\n")
    with pytest.raises(ValidationError, match="after 2024"):
        validate_csv(after, _dataset())


# ---------------------------------------------------------------------------
# ADLS upload: immutable, checksum-named paths (must never overwrite silently)
# ---------------------------------------------------------------------------


class _FakeFileClient:
    def __init__(self, *, exists: bool, size: int) -> None:
        self._exists = exists
        self._size = size
        self.uploaded = False
        self.deleted = False

    def exists(self) -> bool:
        return self._exists

    def get_file_properties(self):
        return type("Props", (), {"size": self._size})()

    def delete_file(self) -> None:
        self.deleted = True
        self._exists = False

    def upload_data(self, data, *, overwrite: bool) -> None:
        assert overwrite is True
        self.uploaded = True


class _FakeFileSystem:
    def __init__(self, clients: dict[str, _FakeFileClient]) -> None:
        self.clients = clients

    def get_file_client(self, path: str) -> _FakeFileClient:
        return self.clients[path]


def _make_writer(
    monkeypatch: pytest.MonkeyPatch, clients: dict[str, _FakeFileClient]
) -> AdlsWriter:
    fake_fs = _FakeFileSystem(clients)
    monkeypatch.setattr(
        "extract.eurostat.adls.DataLakeServiceClient",
        lambda **kwargs: type("Svc", (), {"get_file_system_client": lambda self, name: fake_fs})(),
    )
    monkeypatch.setattr("extract.eurostat.adls.DefaultAzureCredential", lambda: object())
    return AdlsWriter(AdlsConfig(account_name="acct", filesystem="fs"))


DATA_PATH = "raw/eurostat/bop_its6_det/year=2024/bop_its6_det_DE_abc123.csv"
MANIFEST_PATH = "raw/eurostat/bop_its6_det/year=2024/bop_its6_det_DE_abc123.manifest.json"


def _upload(writer: AdlsWriter, tmp_path: Path, content: bytes) -> tuple[str, str]:
    data = tmp_path / "data.csv"
    manifest = tmp_path / "data.manifest.json"
    data.write_bytes(content)
    manifest.write_bytes(b"{}")
    return writer.upload(
        data,
        dataset=_dataset(),
        run_year=2024,
        checksum="abc123",
        manifest_path=manifest,
        partition_value="DE",
    )


def test_adls_upload_writes_checksum_named_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clients = {
        DATA_PATH: _FakeFileClient(exists=False, size=0),
        MANIFEST_PATH: _FakeFileClient(exists=False, size=0),
    }
    writer = _make_writer(monkeypatch, clients)

    data_path, manifest_path = _upload(writer, tmp_path, b"a,b\n1,2\n")

    assert data_path == DATA_PATH
    assert manifest_path == MANIFEST_PATH
    assert clients[DATA_PATH].uploaded
    assert clients[MANIFEST_PATH].uploaded


def test_adls_upload_skips_existing_identical_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    content = b"a,b\n1,2\n"
    clients = {
        DATA_PATH: _FakeFileClient(exists=True, size=len(content)),
        MANIFEST_PATH: _FakeFileClient(exists=True, size=2),
    }
    writer = _make_writer(monkeypatch, clients)

    _upload(writer, tmp_path, content)

    # same checksum-named path and same size => never rewritten
    assert not clients[DATA_PATH].uploaded
    assert not clients[DATA_PATH].deleted
    assert not clients[MANIFEST_PATH].uploaded


def test_adls_upload_replaces_same_name_different_size(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    content = b"a,b\n1,2,3\n"
    clients = {
        DATA_PATH: _FakeFileClient(exists=True, size=999),
        MANIFEST_PATH: _FakeFileClient(exists=False, size=0),
    }
    writer = _make_writer(monkeypatch, clients)

    _upload(writer, tmp_path, content)

    assert clients[DATA_PATH].deleted
    assert clients[DATA_PATH].uploaded
    assert clients[MANIFEST_PATH].uploaded
