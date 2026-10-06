import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from config.settings import DATA_DIR
from models.question import SourceRecord

logger = logging.getLogger(__name__)

class ProvenanceTracker:
    """Tracks source file provenance and verifies file integrity."""

    def __init__(self, provenance_file: Optional[Path] = None):
        """
        Initialize the ProvenanceTracker.

        Args:
            provenance_file (Optional[Path]): Path to the JSON file where records are stored.
        """
        self.provenance_file = provenance_file or (DATA_DIR / "provenance.json")
        self.records: Dict[str, SourceRecord] = {}
        self.load()

    def add_record(self, record: SourceRecord) -> None:
        """
        Add a new source record and save the changes.

        Args:
            record (SourceRecord): The record to add.
        """
        filename = Path(record.file_path).name
        self.records[filename] = record
        self.save()
        logger.info(f"Added provenance record for {filename}")

    def get_record(self, filename: str) -> Optional[SourceRecord]:
        """
        Lookup a source record by its filename.

        Args:
            filename (str): The filename to look up.

        Returns:
            Optional[SourceRecord]: The matching source record or None.
        """
        return self.records.get(filename)

    def get_records_by_source(self, source_type: str) -> List[SourceRecord]:
        """
        Filter records by source type.

        Args:
            source_type (str): The type of source to filter by.

        Returns:
            List[SourceRecord]: A list of matching records.
        """
        return [record for record in self.records.values() if record.source_type == source_type]

    @staticmethod
    def compute_checksum(filepath: Path) -> str:
        """
        Compute the SHA256 checksum of a file.

        Args:
            filepath (Path): The path to the file.

        Returns:
            str: The computed SHA256 hex digest.
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def verify_file(self, filepath: Path) -> bool:
        """
        Verify a file against its stored checksum.

        Args:
            filepath (Path): The path to the file to verify.

        Returns:
            bool: True if the file exists and its checksum matches, False otherwise.
        """
        filename = filepath.name
        record = self.get_record(filename)
        if not record:
            logger.warning(f"No provenance record found for {filename}")
            return False
        
        if not filepath.exists():
            logger.warning(f"File {filepath} does not exist.")
            return False

        current_checksum = self.compute_checksum(filepath)
        is_valid = (current_checksum == record.checksum)
        if not is_valid:
            logger.warning(f"Checksum mismatch for {filename}: expected {record.checksum}, got {current_checksum}")
        return is_valid

    def save(self) -> None:
        """Save the provenance records to a JSON file."""
        self.provenance_file.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for filename, record in self.records.items():
            # Handle Path object serialization
            record_dict = {
                "source_url": record.source_url,
                "file_path": str(record.file_path),
                "checksum": record.checksum,
                "source_type": record.source_type,
                "metadata": record.metadata
            }
            data[filename] = record_dict

        with open(self.provenance_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        logger.debug(f"Saved provenance data to {self.provenance_file}")

    def load(self) -> None:
        """Load the provenance records from the JSON file."""
        if not self.provenance_file.exists():
            logger.info(f"Provenance file {self.provenance_file} does not exist. Starting fresh.")
            return

        with open(self.provenance_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for filename, record_dict in data.items():
                    self.records[filename] = SourceRecord(
                        source_url=record_dict["source_url"],
                        file_path=Path(record_dict["file_path"]),
                        checksum=record_dict["checksum"],
                        source_type=record_dict["source_type"],
                        metadata=record_dict.get("metadata", {})
                    )
                logger.info(f"Loaded {len(self.records)} records from {self.provenance_file}")
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from {self.provenance_file}. Starting fresh.")

    def generate_report(self) -> dict:
        """
        Generate summary statistics of all tracked files.

        Returns:
            dict: Summary statistics including total count and counts per source type.
        """
        report: Dict[str, Any] = {
            "total_files": len(self.records),
            "by_source_type": {}
        }
        for record in self.records.values():
            stype = record.source_type
            report["by_source_type"][stype] = report["by_source_type"].get(stype, 0) + 1
            
        return report
