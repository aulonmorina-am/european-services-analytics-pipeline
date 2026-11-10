from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlencode

import requests

from .models import DatasetConfig


class EurostatRequestError(RuntimeError):
    """Raised when Eurostat cannot provide a dataset response."""


class EurostatClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        *,
        timeout_seconds: float = 120.0,
        max_attempts: int = 4,
        backoff_seconds: float = 2.0,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds

    def download(
        self,
        dataset: DatasetConfig,
        destination: Path,
    ) -> str:
        url = build_data_url(dataset)
        destination.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(1, self.max_attempts + 1):
            try:
                with self.session.get(
                    url,
                    headers={"Accept": "text/csv"},
                    stream=True,
                    timeout=self.timeout_seconds,
                ) as response:
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == self.max_attempts:
                            raise EurostatRequestError(
                                f"Eurostat returned HTTP {response.status_code} for {dataset.code}"
                            )
                        time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))
                        continue
                    if response.status_code != 200:
                        raise EurostatRequestError(
                            f"Eurostat returned HTTP {response.status_code} for {dataset.code}"
                        )

                    with destination.open("wb") as output:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                output.write(chunk)
                    return url
            except requests.RequestException as exc:
                if attempt == self.max_attempts:
                    raise EurostatRequestError(
                        f"Eurostat request failed for {dataset.code}: {exc}"
                    ) from exc
                time.sleep(self.backoff_seconds * (2 ** (attempt - 1)))

        raise EurostatRequestError(f"Eurostat request failed for {dataset.code}")


def build_data_url(dataset: DatasetConfig) -> str:
    query: dict[str, str] = {"format": dataset.format}
    if dataset.start_period:
        query["startPeriod"] = dataset.start_period
    if dataset.end_period:
        query["endPeriod"] = dataset.end_period
    query.update(dataset.filters)

    params = urlencode(query)
    return f"{dataset.endpoint.rstrip('/')}/{dataset.code}?{params}"
