#!/usr/bin/env python3
"""Perform the post-release housekeeping edits for a PedPy release.

These are the deterministic edits that used to be done by hand (see the
``update supported versions`` / ``add placeholder in changelog`` / ``add
snapshot to citation file`` commits):

* ``CITATION.cff``      -- add the freshly archived Zenodo snapshot for the
                           released version and (optionally) bump the
                           ``version:`` field to ``<released>-dev``.
* ``docs/source/changelog.rst`` -- prepend an empty placeholder section for the
                           next development version. ``minor`` placeholders get
                           the full template, ``patch`` placeholders only a
                           ``**Fixes:**`` section.
* ``SECURITY.md``       -- mark the released version as supported and flip the
                           previously supported version to unsupported.
* ``README.md``         -- refresh the BibTeX citation example.

Which of these run is controlled by the ``--citation`` / ``--changelog`` /
``--security`` / ``--readme`` flags. With none of them given, all four run with
``minor`` defaults (convenient for a local minor-release dry run). The GitHub
Actions workflow selects the right subset for each target branch and release
type.

The Zenodo DOI / publication date are looked up from the Zenodo API (shared
:mod:`zenodo` helper) unless supplied via ``--zenodo-doi`` / ``--pub-date``.

Every edit is idempotent: re-running for an already-prepared version leaves the
files unchanged. Committing / opening PRs is left to the caller.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from zenodo import find_record_for_version, normalize_version

BIBTEX_MONTHS = [
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]


@dataclass
class ReleaseInfo:
    """Everything needed to rewrite the citation-related files."""

    version: str  # released version, e.g. "1.5.0" (no leading "v")
    doi: str  # full DOI, e.g. "10.5281/zenodo.20511313"
    record_id: str  # Zenodo numeric record id, e.g. "20511313"
    pub_date: date  # publication date of the archived record


# --------------------------------------------------------------------------- #
# Version helpers
# --------------------------------------------------------------------------- #
def bump_minor(version: str) -> str:
    """Return the next minor version (``1.5.0`` -> ``1.6.0``)."""
    major, minor, _patch = _version_parts(version)
    return f"{major}.{minor + 1}.0"


def bump_patch(version: str) -> str:
    """Return the next patch version (``1.5.0`` -> ``1.5.1``)."""
    major, minor, patch = _version_parts(version)
    return f"{major}.{minor}.{patch + 1}"


def _version_parts(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) < 3 or not all(p.isdigit() for p in parts[:3]):
        raise ValueError(f"expected an X.Y.Z version, got {version!r}")
    return int(parts[0]), int(parts[1]), int(parts[2])


# --------------------------------------------------------------------------- #
# File edits
# --------------------------------------------------------------------------- #
def update_citation(path: Path, info: ReleaseInfo, *, bump_version: bool) -> bool:
    """Add the new snapshot entry and, optionally, bump the ``version:`` field."""
    text = path.read_text(encoding="utf-8")
    changed = False

    entry = (
        f"  - description: This is the archived snapshot of version "
        f"{info.version} of PedPy\n"
        f"    type: doi\n"
        f'    value: "{info.doi}"\n'
    )
    if info.doi not in text and f"version {info.version} of PedPy" not in text:
        # Insert right after the "collection of archived snapshots" entry so the
        # per-version list stays newest-first.
        anchor = re.search(
            r"(  - description: This is the collection of archived snapshots.*?\n"
            r"    type: doi\n"
            r'    value: "[^"]+"\n)',
            text,
            flags=re.DOTALL,
        )
        if anchor is None:
            raise ValueError("could not locate the collection DOI entry in CITATION.cff")
        insert_at = anchor.end()
        text = text[:insert_at] + entry + text[insert_at:]
        changed = True

    if bump_version:
        new_version_line = f"version: {info.version}-dev"
        updated, n = re.subn(
            r"^version:[ \t]*\S+[ \t]*$",
            new_version_line,
            text,
            flags=re.MULTILINE,
        )
        if n and updated != text:
            text = updated
            changed = True

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def update_changelog(path: Path, next_version: str, *, kind: str) -> bool:
    """Prepend an empty placeholder section for ``next_version``.

    ``kind`` is ``"minor"`` (full template) or ``"patch"`` (fixes only).
    """
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^Version {re.escape(next_version)} ", text, flags=re.MULTILINE):
        return False  # placeholder already present

    if kind == "patch":
        sections = "**Fixes:**\n\n"
    else:
        sections = "**New features:**\n\n**What's changed:**\n\n**Fixes:**\n\n"

    title = f"Version {next_version} (YYYY-MM-DD)"
    block = f"{title}\n{'=' * len(title)}\n\n{sections}\n"

    # Insert directly after the top-level "Changelog" title underline.
    anchor = re.search(r"^\*{3,}\nChangelog\n\*{3,}\n\n", text, flags=re.MULTILINE)
    if anchor is None:
        raise ValueError("could not locate the Changelog header in changelog.rst")
    insert_at = anchor.end()
    text = text[:insert_at] + block + text[insert_at:]
    path.write_text(text, encoding="utf-8")
    return True


def update_security(path: Path, info: ReleaseInfo) -> bool:
    """Mark the released version supported; flip the previous one to :x:."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    if any(re.match(rf"\|\s*{re.escape(info.version)}\s*\|", line) for line in lines):
        return False  # already listed

    check = ":white_check_mark:"
    new_row = f"| {info.version}   | {check} |\n"
    out: list[str] = []
    inserted = False
    for line in lines:
        if not inserted and check in line:
            out.append(new_row)
            out.append(line.replace(check, ":x:"))
            inserted = True
        else:
            out.append(line)

    if not inserted:
        raise ValueError("could not find a supported version row in SECURITY.md")

    path.write_text("".join(out), encoding="utf-8")
    return True


def update_readme(path: Path, info: ReleaseInfo) -> bool:
    """Rewrite the BibTeX citation example for the released version."""
    text = path.read_text(encoding="utf-8")
    month = BIBTEX_MONTHS[info.pub_date.month - 1]
    year = info.pub_date.year
    key = f"schrodter_{year}_{info.record_id}"
    doi = info.doi

    bibtex = (
        "```\n"
        f"@software{{{key},\n"
        "  author       = {Schrödter, Tobias and\n"
        "                  The PedPy Development Team},\n"
        "  title        = {PedPy - Pedestrian Trajectory Analyzer},\n"
        f"  month        = {month},\n"
        f"  year         = {year},\n"
        "  publisher    = {Zenodo},\n"
        f"  version      = {{v{info.version}}},\n"
        f"  doi          = {{{doi}}},\n"
        f"  url          = {{https://doi.org/{doi}}},\n"
        "}\n"
        "```"
    )

    original = text

    # Replace the "For the latest release (v.X)" line.
    text = re.sub(
        r"For the latest release \(v\.?[^)]*\) the BibTeX entry is:",
        f"For the latest release (v.{info.version}) the BibTeX entry is:",
        text,
    )

    # Replace the fenced code block that contains the @software entry.
    text, n2 = re.subn(
        r"```\n@software\{.*?\n```",
        lambda _m: bibtex,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if not n2:
        raise ValueError("could not locate the BibTeX code block in README.md")

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        required=True,
        help="Released version, e.g. 1.5.0 (a leading 'v' is stripped).",
    )
    parser.add_argument(
        "--zenodo-doi",
        help="Override the DOI instead of fetching it from Zenodo.",
    )
    parser.add_argument(
        "--pub-date",
        help="Override the publication date (YYYY-MM-DD). Requires --zenodo-doi.",
    )
    parser.add_argument("--retries", type=int, default=1, help="Zenodo poll attempts.")
    parser.add_argument("--delay", type=float, default=30.0, help="Seconds between Zenodo polls.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root (default: parent of this script's directory).",
    )

    edits = parser.add_argument_group("edits (default: all, as for a minor release)")
    edits.add_argument("--citation", action="store_true", help="Add the Zenodo snapshot entry.")
    edits.add_argument(
        "--no-citation-version-bump",
        action="store_true",
        help="With --citation, do not touch the CITATION.cff 'version:' field.",
    )
    edits.add_argument(
        "--changelog",
        choices=("minor", "patch"),
        help="Add a next-version changelog placeholder of this kind.",
    )
    edits.add_argument(
        "--changelog-version",
        help="Explicit version for the placeholder (default: derived from --version).",
    )
    edits.add_argument("--security", action="store_true", help="Update the SECURITY.md table.")
    edits.add_argument("--readme", action="store_true", help="Refresh the README BibTeX entry.")
    return parser.parse_args(argv)


def resolve_release_info(args: argparse.Namespace) -> ReleaseInfo:
    """Build the :class:`ReleaseInfo`, fetching from Zenodo unless overridden."""
    version = normalize_version(args.version)

    if args.zenodo_doi:
        match = re.search(r"zenodo\.(\d+)", args.zenodo_doi)
        if not match:
            raise SystemExit(f"could not parse a record id from {args.zenodo_doi!r}")
        pub = date.fromisoformat(args.pub_date) if args.pub_date else date.today()
        return ReleaseInfo(
            version=version,
            doi=args.zenodo_doi,
            record_id=match.group(1),
            pub_date=pub,
        )

    print(f"Looking up Zenodo record for version {version} ...")
    record = find_record_for_version(version, retries=args.retries, delay=args.delay)
    return ReleaseInfo(
        version=version,
        doi=record.doi,
        record_id=record.record_id,
        pub_date=record.publication_date,
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point: resolve the release info and apply the selected edits."""
    args = parse_args(argv)
    info = resolve_release_info(args)
    root: Path = args.repo_root

    # Default: no edit flags -> do everything as for a minor release.
    default_all = not (args.citation or args.changelog or args.security or args.readme)
    do_citation = args.citation or default_all
    do_security = args.security or default_all
    do_readme = args.readme or default_all
    changelog_kind = args.changelog or ("minor" if default_all else None)

    print(
        f"Preparing release housekeeping:\n"
        f"  released version : {info.version}\n"
        f"  DOI              : {info.doi}\n"
        f"  publication date : {info.pub_date.isoformat()}\n"
    )

    edits: dict[str, bool] = {}
    if do_citation:
        edits["CITATION.cff"] = update_citation(
            root / "CITATION.cff",
            info,
            bump_version=not args.no_citation_version_bump,
        )
    if changelog_kind:
        next_version = args.changelog_version or (
            bump_patch(info.version) if changelog_kind == "patch" else bump_minor(info.version)
        )
        edits["docs/source/changelog.rst"] = update_changelog(
            root / "docs" / "source" / "changelog.rst",
            normalize_version(next_version),
            kind=changelog_kind,
        )
    if do_security:
        edits["SECURITY.md"] = update_security(root / "SECURITY.md", info)
    if do_readme:
        edits["README.md"] = update_readme(root / "README.md", info)

    for name, changed in edits.items():
        print(f"  {'updated ' if changed else 'no change'} {name}")

    if not any(edits.values()):
        print("\nNothing to do -- everything is already prepared.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
