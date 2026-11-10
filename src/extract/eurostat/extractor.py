from __future__ import annotations

import logging
import tempfile
from dataclasses import replace
from pathlib import Path

from .adls import AdlsWriter
from .client import EurostatClient
from .config import get_dataset, load_adls_config, load_extractor_config
from .manifest import write_manifest
from .models import ExtractionRequest
from .validation import validate_csv

logger = logging.getLogger(__name__)


def run(
    *,
    config_path: Path = Path("config/datasets.yaml"),
    datasets: tuple[str, ...] | None = None,
    run_year: int | None = None,
) -> None:
    config = load_extractor_config(config_path)
    selected = datasets or tuple(config.datasets)
    client = EurostatClient()
    adls_writer = AdlsWriter(load_adls_config())

    for code in selected:
        dataset = get_dataset(config, code)
        years = (run_year,) if run_year is not None else _configured_years(dataset)
        for year in years:
            annual_dataset = replace(
                dataset,
                start_period=str(year),
                end_period=str(year),
            )
            request = ExtractionRequest(dataset=annual_dataset, run_year=year)
            _run_dataset(request, client, adls_writer)


def _configured_years(dataset) -> tuple[int, ...]:
    if not dataset.start_period or not dataset.end_period:
        raise ValueError(
            f"Annual extraction requires start_period and end_period for {dataset.code}."
        )
    start_year = int(dataset.start_period[:4])
    end_year = int(dataset.end_period[:4])
    if end_year < start_year:
        raise ValueError(f"Invalid period range for {dataset.code}.")
    return tuple(range(start_year, end_year + 1))


def _run_dataset(
    request: ExtractionRequest,
    client: EurostatClient,
    adls_writer: AdlsWriter,
) -> None:
    dataset = request.dataset
    with tempfile.TemporaryDirectory(prefix=f"eurostat-{dataset.code}-") as directory:
        data_path = Path(directory) / f"{dataset.code}.csv"
        manifest_path = Path(directory) / f"{dataset.code}.manifest.json"

        logger.info("dataset_download_started dataset=%s", dataset.code)
        source_url = client.download(dataset, data_path)
        validation = validate_csv(data_path, dataset)
        write_manifest(
            manifest_path,
            dataset=dataset,
            source_url=source_url,
            validation=validation,
        )
        data_adls_path, manifest_adls_path = adls_writer.upload(
            data_path,
            dataset=dataset,
            run_year=request.run_year,
            checksum=validation.checksum,
            manifest_path=manifest_path,
        )
        logger.info(
            "dataset_published dataset=%s rows=%d bytes=%d data_path=%s manifest_path=%s",
            dataset.code,
            validation.row_count,
            validation.byte_count,
            data_adls_path,
            manifest_adls_path,
        )
