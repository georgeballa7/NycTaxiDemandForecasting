import shutil
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from backend.src.config.settings import RAW_DATA_DIR
from backend.src.ingestion.tlc_availability import build_yellow_taxi_url


def download_yellow_taxi_month(
    year: int,
    month: int,
    raw_data_path: Path = RAW_DATA_DIR,
) -> Path:
    """Download one NYC TLC Yellow Taxi monthly Parquet file atomically."""

    if not 1 <= month <= 12:
        raise ValueError(
            f"month must be between 1 and 12. Received: {month}"
        )

    raw_data_path.mkdir(parents=True, exist_ok=True)

    destination = (
        raw_data_path
        / f"yellow_tripdata_{year}-{month:02d}.parquet"
    )

    if destination.exists() and destination.stat().st_size > 0:
        print(f"TLC file already exists: {destination}")
        return destination

    url = build_yellow_taxi_url(year, month)
    temporary = destination.with_suffix(".parquet.part")

    temporary.unlink(missing_ok=True)

    print(f"Downloading TLC data: {url}")

    try:
        with urlopen(url, timeout=120) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Unexpected TLC response status: {response.status}"
                )

            with temporary.open("wb") as target:
                shutil.copyfileobj(response, target)

        if not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError(
                f"Downloaded TLC file is empty: {url}"
            )

        temporary.replace(destination)

    except HTTPError as exc:
        temporary.unlink(missing_ok=True)
        if exc.code == 404:
            raise FileNotFoundError(
                f"TLC dataset is not available: {url}"
            ) from exc
        raise

    except (URLError, OSError, RuntimeError):
        temporary.unlink(missing_ok=True)
        raise

    print(f"TLC file downloaded successfully: {destination}")
    return destination
