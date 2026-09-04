from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def build_yellow_taxi_url(year: int, month: int) -> str:
    filename = f"yellow_tripdata_{year}-{month:02d}.parquet"
    return f"{BASE_URL}/{filename}"


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1

    return year, month + 1


def is_month_available(year: int, month: int) -> bool:
    url = build_yellow_taxi_url(year, month)

    try:
        head_request = Request(url, method="HEAD")

        with urlopen(head_request, timeout=15) as response:
            return response.status == 200

    except HTTPError as exc:
        if exc.code == 404:
            return False

        if exc.code != 403:
            raise

        # Some TLC/CDN responses reject HEAD requests with 403.
        # Fall back to a minimal ranged GET before deciding that
        # the monthly file is unavailable.
        get_request = Request(
            url,
            headers={"Range": "bytes=0-0"},
            method="GET",
        )

        try:
            with urlopen(get_request, timeout=15) as response:
                return response.status in (200, 206)

        except HTTPError as get_exc:
            if get_exc.code in (403, 404):
                return False
            raise

    except URLError as exc:
        raise ConnectionError(
            f"Could not reach TLC data source: {exc}"
        ) from exc


if __name__ == "__main__":
    last_processed_year = 2025
    last_processed_month = 6

    year, month = next_month(
        last_processed_year,
        last_processed_month,
    )

    url = build_yellow_taxi_url(year, month)
    available = is_month_available(year, month)

    print(f"Next month: {year}-{month:02d}")
    print(f"URL: {url}")
    print(f"Available: {available}")
