"""Shared Zenodo lookup helpers.

Both the release automation (``scripts/prepare_release.py``) and the docs build
(``scripts/generate_bibtex.py``) need to locate the Zenodo record for a specific
PedPy version. That logic lives here so there is a single place that talks to
the Zenodo API.

Run directly to resolve a version and print the result as ``key=value`` lines
(handy for GitHub Actions step outputs)::

    python scripts/zenodo.py --version 1.5.0
    doi=10.5281/zenodo.20511313
    record_id=20511313
    publication_date=2026-06-02
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import requests

# Concept (all-versions) DOI of PedPy on Zenodo.
CONCEPT_DOI = "10.5281/zenodo.7194992"
# Free-text query used to list PedPy's records; matching is done on the version.
SEARCH_QUERY = "PedPy"
API_URL = "https://zenodo.org/api/records"


@dataclass
class ZenodoRecord:
    """A single archived Zenodo version of PedPy."""

    version: str  # normalized, without a leading "v", e.g. "1.5.0"
    record_id: str  # numeric Zenodo record id, e.g. "20511313"
    doi: str  # full DOI, e.g. "10.5281/zenodo.20511313"
    publication_date: date


def normalize_version(raw: str) -> str:
    """Strip a leading ``v`` and surrounding whitespace from a version string."""
    return raw.strip().lstrip("vV")


def _parse_date(raw: str) -> date:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return date.today()


def _to_record(hit: dict[str, Any], version: str) -> ZenodoRecord:
    doi = str(hit.get("doi") or hit.get("metadata", {}).get("doi", ""))
    match = re.search(r"zenodo\.(\d+)", doi)
    record_id = match.group(1) if match else str(hit.get("id", ""))
    if not doi and record_id:
        doi = f"10.5281/zenodo.{record_id}"
    raw_date = str(hit.get("metadata", {}).get("publication_date") or hit.get("created", ""))
    return ZenodoRecord(
        version=version,
        record_id=record_id,
        doi=doi,
        publication_date=_parse_date(raw_date),
    )


def _list_records(*, timeout: float = 30.0) -> list[dict[str, Any]]:
    response = requests.get(
        API_URL,
        params={"q": SEARCH_QUERY, "all_versions": True, "sort": "mostrecent", "size": 25},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json().get("hits", {}).get("hits", [])


def find_record_for_version(
    version: str,
    *,
    retries: int = 10,
    delay: float = 2.0,
) -> ZenodoRecord:
    """Return the Zenodo record whose version matches ``version``.

    Keeps polling (``retries`` attempts, ``delay`` seconds apart) until a
    matching record shows up, to bridge the gap between publishing a GitHub
    release and Zenodo finishing the archival.
    """
    target = normalize_version(version)
    seen: set[str] = set()
    for attempt in range(1, retries + 1):
        try:
            hits = _list_records()
        except requests.RequestException as exc:
            warnings.warn(
                f"Zenodo request failed (attempt {attempt}/{retries}): {exc}",
                stacklevel=2,
            )
            hits = []

        for hit in hits:
            hit_version = normalize_version(str(hit.get("metadata", {}).get("version", "")))
            if hit_version == target:
                return _to_record(hit, target)
            if hit_version:
                seen.add(hit_version)

        if attempt < retries:
            time.sleep(delay)

    raise RuntimeError(
        f"No Zenodo record for version {target!r} after {retries} attempt(s). "
        f"Seen versions: {sorted(seen) or '<none>'}. Archival may be unfinished."
    )


def fetch_bibtex(
    record_id: str,
    *,
    retries: int = 10,
    delay: float = 2.0,
    timeout: float = 30.0,
) -> str:
    """Fetch the BibTeX representation of a Zenodo record."""
    url = f"{API_URL}/{record_id}"
    headers = {"accept": "application/x-bibtex"}
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = "utf-8"
            return response.text
        except requests.RequestException as exc:
            warnings.warn(
                f"BibTeX fetch failed (attempt {attempt}/{retries}): {exc}",
                stacklevel=2,
            )
            if attempt < retries:
                time.sleep(delay)
    raise RuntimeError(f"Could not fetch BibTeX for record {record_id!r}.")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve a PedPy Zenodo record.")
    parser.add_argument("--version", required=True, help="Version, e.g. 1.5.0.")
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args(argv)

    record = find_record_for_version(args.version, retries=args.retries, delay=args.delay)
    print(f"doi={record.doi}")
    print(f"record_id={record.record_id}")
    print(f"publication_date={record.publication_date.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
