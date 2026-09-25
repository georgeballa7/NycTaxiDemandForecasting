from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"


def build_yellow_taxi_url(year: int, month: int) -> str:
    """Build the public TLC URL for one Yellow Taxi monthly Parquet file.

    Parameters
    ----------
    year : int
        Calendar year used in the TLC filename.
    month : int
        Calendar month used in the TLC filename.

    Returns
    -------
    str
        Fully qualified URL of the requested TLC dataset.
    """
    filename = f"yellow_tripdata_{year}-{month:02d}.parquet"
    return f"{BASE_URL}/{filename}"


def next_month(year: int, month: int) -> tuple[int, int]:
    """Return the calendar month immediately following the supplied month.

    Parameters
    ----------
    year : int
        Current calendar year.
    month : int
        Current calendar month.

    Returns
    -------
    tuple[int, int]
        Year and month of the next calendar month, including year rollover
        from December to January.
    """
    if month == 12:
        return year + 1, 1

    return year, month + 1


def is_month_available(year: int, month: int) -> bool:
    """Check whether a monthly Yellow Taxi file is available from TLC.

    Parameters
    ----------
    year : int
        Calendar year of the dataset to check.
    month : int
        Calendar month of the dataset to check.

    Returns
    -------
    bool
        True when the remote file responds successfully, otherwise False for
        an unavailable 403/404 response.

    Raises
    ------
    ConnectionError
        If the TLC data source cannot be reached.
    HTTPError
        For unexpected HTTP failures.

    Notes
    -----
    A HEAD request is attempted first. Because the TLC/CDN can reject HEAD
    with HTTP 403, the function falls back to a one-byte ranged GET before
    deciding that the file is unavailable.
    """
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
