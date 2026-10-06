"""
Downloader module for fetching GATE CSE papers from GitHub releases
and the official GATE portal.
"""
import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from tqdm import tqdm

from models.question import SourceRecord, SourceType

logger = logging.getLogger(__name__)


class GATEDownloader:
    """Downloads GATE CSE papers from GATEOverflow GitHub and official portal."""

    GITHUB_API_URL = "https://api.github.com/repos/GATEOverflow/GO-PDFs/releases?per_page=50"

    # Release tags and their expected assets
    TARGET_RELEASES = {
        "gatecse-2027": ["filter1_volume1.pdf", "filter1_volume2.pdf", "filter1_volume3.pdf"],
        "gatecse-2026": ["volume1.pdf", "volume2.pdf"],
        "gatecse-2025": ["volume1.pdf", "volume2.pdf"],
        "gatecse-2024": ["filter1_volume1.pdf", "filter1_volume2.pdf", "filter1_volume3.pdf"],
        "gatecse-2022-vol1,2": ["Volume-1.pdf", "Volume-2.pdf", "Volume-3.pdf"],
        "gate-2026-common": ["em.pdf"],
        "engineering-mathematics": ["em.pdf"],
        "aptitude": ["aptitude.pdf"],
    }

    # Official GATE portal paper URLs (CS papers + answer keys)
    OFFICIAL_PAPERS = {
        2025: [
            ("https://gate2026.iitg.ac.in/doc/download/2025/CS12025.pdf", "CS1_2025.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2025/CS22025.pdf", "CS2_2025.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2025_Key/CS1_Keys.pdf", "CS1_2025_Key.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2025_Key/CS2_Keys.pdf", "CS2_2025_Key.pdf"),
        ],
        2024: [
            ("https://gate2026.iitg.ac.in/doc/download/2024/CS124S5.pdf", "CS1_2024.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2024/CS224S6.pdf", "CS2_2024.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2024/CS1FinalAnswerKey.pdf", "CS1_2024_Key.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2024/CS2FinalAnswerKey.pdf", "CS2_2024_Key.pdf"),
        ],
        2023: [
            ("https://gate2026.iitg.ac.in/doc/download/2023/cs1_2023.pdf", "CS1_2023.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2023/cs2_2023.pdf", "CS2_2023.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2023/CS1_ANS_GATE2023.pdf", "CS1_2023_Key.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2023/CS2_ANS_GATE2023.pdf", "CS2_2023_Key.pdf"),
        ],
        2022: [
            ("https://gate2026.iitg.ac.in/doc/download/2022/CS1-cs22-s1.pdf", "CS1_2022.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2022/CS2-cs22-s2.pdf", "CS2_2022.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2022/CS1-Key.pdf", "CS1_2022_Key.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2022/CS2-Key.pdf", "CS2_2022_Key.pdf"),
        ],
        2021: [
            ("https://gate2026.iitg.ac.in/doc/download/2021/CS_21.pdf", "CS_2021.pdf"),
            ("https://gate2026.iitg.ac.in/doc/download/2021/CS_21_key.pdf", "CS_2021_Key.pdf"),
        ],
    }

    def __init__(self, data_dir: Path) -> None:
        """Initialize with data directory path."""
        self.data_dir = Path(data_dir)
        self.go_dir = self.data_dir / "raw" / "gateoverflow"
        self.official_dir = self.data_dir / "raw" / "official"
        self.go_dir.mkdir(parents=True, exist_ok=True)
        self.official_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        """Compute SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(8192), b""):
                sha256_hash.update(block)
        return sha256_hash.hexdigest()

    def _download_file(self, url: str, dest_path: Path) -> Optional[str]:
        """Download a file with progress bar. Returns SHA256 or None on failure."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists() and dest_path.stat().st_size > 0:
            logger.info(f"Already exists, skipping: {dest_path.name}")
            return self._compute_sha256(dest_path)

        logger.info(f"Downloading: {dest_path.name}")
        try:
            resp = requests.get(url, stream=True, timeout=60,
                                headers={"Accept": "application/octet-stream"})
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))

            sha = hashlib.sha256()
            with open(dest_path, "wb") as f, tqdm(
                desc=dest_path.name, total=total,
                unit="B", unit_scale=True, unit_divisor=1024,
            ) as bar:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    sha.update(chunk)
                    bar.update(len(chunk))
            return sha.hexdigest()

        except requests.RequestException as e:
            logger.warning(f"Download failed for {url}: {e}")
            if dest_path.exists():
                dest_path.unlink()
            return None

    def _make_record(self, filepath: Path, source_type: SourceType,
                     url: str, year_range: str, checksum: str) -> SourceRecord:
        """Create a SourceRecord for a downloaded file."""
        return SourceRecord(
            filename=filepath.name,
            source_type=source_type,
            source_url=url,
            download_date=datetime.now(),
            file_checksum=checksum,
            file_size=filepath.stat().st_size,
            year_range=year_range,
            verified=True,
        )

    def download_go_releases(self) -> List[SourceRecord]:
        """Download GATE CSE PDFs from GATEOverflow GitHub releases."""
        logger.info("Fetching GATEOverflow release catalog...")
        records: List[SourceRecord] = []

        try:
            resp = requests.get(self.GITHUB_API_URL, timeout=30)
            resp.raise_for_status()
            releases = resp.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GitHub releases: {e}")
            return records

        for release in releases:
            tag = release.get("tag_name", "")
            if tag not in self.TARGET_RELEASES:
                continue

            expected_assets = self.TARGET_RELEASES[tag]
            tag_dir = self.go_dir / tag
            tag_dir.mkdir(parents=True, exist_ok=True)

            for asset in release.get("assets", []):
                name = asset.get("name", "")
                if name not in expected_assets:
                    continue

                url = asset["browser_download_url"]
                dest = tag_dir / name
                checksum = self._download_file(url, dest)
                if checksum:
                    records.append(self._make_record(
                        dest, SourceType.GATEOVERFLOW, url, "1987-2026", checksum
                    ))

        logger.info(f"GO releases: {len(records)} files ready")
        return records

    def download_official_papers(self, start_year: int = 2021,
                                  end_year: int = 2025) -> List[SourceRecord]:
        """Download CS papers + answer keys from the official GATE portal."""
        logger.info(f"Downloading official papers ({start_year}-{end_year})...")
        records: List[SourceRecord] = []

        for year in range(start_year, end_year + 1):
            if year not in self.OFFICIAL_PAPERS:
                continue
            year_dir = self.official_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)

            for url, filename in self.OFFICIAL_PAPERS[year]:
                dest = year_dir / filename
                checksum = self._download_file(url, dest)
                if checksum:
                    records.append(self._make_record(
                        dest, SourceType.OFFICIAL, url, str(year), checksum
                    ))

        logger.info(f"Official papers: {len(records)} files ready")
        return records

    def organize_user_provided(self) -> List[SourceRecord]:
        """Scan data/raw/official/ for user-provided PDFs and create records."""
        logger.info("Scanning for user-provided papers...")
        records: List[SourceRecord] = []

        for pdf in self.official_dir.rglob("*.pdf"):
            # Detect year from parent dir or filename
            year = None
            if re.match(r"^(19|20)\d{2}$", pdf.parent.name):
                year = int(pdf.parent.name)
            else:
                m = re.search(r"(19|20)\d{2}", pdf.name)
                if m:
                    year = int(m.group(0))

            checksum = self._compute_sha256(pdf)
            records.append(self._make_record(
                pdf, SourceType.OFFICIAL, "user_provided",
                str(year) if year else "unknown", checksum
            ))

        logger.info(f"User-provided: {len(records)} files found")
        return records

    def download_all(self) -> Dict[str, Any]:
        """Run all downloads. Returns summary statistics."""
        go = self.download_go_releases()
        official = self.download_official_papers()
        user = self.organize_user_provided()

        summary = {
            "go_releases": len(go),
            "official_papers": len(official),
            "user_provided": len(user),
            "total_files": len(go) + len(official) + len(user),
        }
        logger.info(f"Download complete: {json.dumps(summary)}")
        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    from config.settings import DATA_DIR
    dl = GATEDownloader(DATA_DIR)
    print(json.dumps(dl.download_all(), indent=2))
