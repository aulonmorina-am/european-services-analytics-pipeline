from __future__ import annotations

from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

from .models import AdlsConfig, DatasetConfig


class AdlsWriter:
    def __init__(self, config: AdlsConfig) -> None:
        service_client = DataLakeServiceClient(
            account_url=f"https://{config.account_name}.dfs.core.windows.net",
            credential=DefaultAzureCredential(),
        )
        self.filesystem = service_client.get_file_system_client(config.filesystem)
        self.root_path = config.root_path.strip("/")

    def upload(
        self,
        local_path: Path,
        *,
        dataset: DatasetConfig,
        run_year: int,
        checksum: str,
        manifest_path: Path,
        partition_value: str | None = None,
    ) -> tuple[str, str]:
        prefix = f"{self.root_path}/{dataset.code}/year={run_year}"
        partition_suffix = f"_{partition_value}" if partition_value else ""
        stem = f"{dataset.code}{partition_suffix}_{checksum}"
        data_path = f"{prefix}/{stem}.csv"
        manifest_adls_path = f"{prefix}/{stem}.manifest.json"

        self._upload_new(local_path, data_path)
        self._upload_new(manifest_path, manifest_adls_path)
        return data_path, manifest_adls_path

    def _upload_new(self, local_path: Path, adls_path: str) -> None:
        file_client = self.filesystem.get_file_client(adls_path)
        if file_client.exists():
            properties = file_client.get_file_properties()
            if properties.size == local_path.stat().st_size:
                return
            file_client.delete_file()
        with local_path.open("rb") as input_file:
            file_client.upload_data(input_file, overwrite=True)
