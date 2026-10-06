"""
Data models for the GATE CSE Exam Pattern Forecasting System.
"""
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime

class QuestionType(Enum):
    MCQ = "MCQ"
    MSQ = "MSQ"
    NAT = "NAT"

class SourceType(Enum):
    OFFICIAL = "OFFICIAL"
    GATEOVERFLOW = "GATEOVERFLOW"

class ExtractionQuality(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    FAILED = "FAILED"

class MatchStatus(Enum):
    AUTO_VERIFIED = "AUTO_VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNMATCHED_OFFICIAL = "UNMATCHED_OFFICIAL"
    GO_ONLY = "GO_ONLY"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"

class CoverageStatus(Enum):
    BOTH_SOURCES = "BOTH_SOURCES"
    OFFICIAL_ONLY = "OFFICIAL_ONLY"
    GO_ONLY = "GO_ONLY"
    OFFICIAL_SOURCE_MISSING = "OFFICIAL_SOURCE_MISSING"
    GO_SOURCE_MISSING = "GO_SOURCE_MISSING"

@dataclass
class RawQuestion:
    year: int
    session: str
    question_number: int
    raw_text: str
    source_file: str
    page_numbers: list[int]

@dataclass
class StructuredQuestion:
    id: str
    year: int
    session: str
    question_number: int
    question_text: str
    options: Dict[str, str]
    question_type: QuestionType
    marks: float
    correct_answer: str
    source: SourceType
    source_url: str
    source_file: str
    extraction_date: datetime
    raw_text: str
    checksum: str
    go_subject: Optional[str] = None
    go_topic: Optional[str] = None
    go_url: Optional[str] = None
    extraction_quality: Optional[ExtractionQuality] = None
    extraction_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the question to a dictionary."""
        data = asdict(self)
        if isinstance(self.question_type, QuestionType):
            data["question_type"] = self.question_type.value
        if isinstance(self.source, SourceType):
            data["source"] = self.source.value
        if self.extraction_quality and isinstance(self.extraction_quality, ExtractionQuality):
            data["extraction_quality"] = self.extraction_quality.value
        if isinstance(self.extraction_date, datetime):
            data["extraction_date"] = self.extraction_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuredQuestion':
        """Create a question from a dictionary."""
        d = data.copy()
        if "question_type" in d and isinstance(d["question_type"], str):
            d["question_type"] = QuestionType(d["question_type"])
        if "source" in d and isinstance(d["source"], str):
            d["source"] = SourceType(d["source"])
        if "extraction_quality" in d and d["extraction_quality"] is not None and isinstance(d["extraction_quality"], str):
            d["extraction_quality"] = ExtractionQuality(d["extraction_quality"])
        if "extraction_date" in d and isinstance(d["extraction_date"], str):
            d["extraction_date"] = datetime.fromisoformat(d["extraction_date"])
            
        # Ignore extra keys not present in StructuredQuestion fields
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(cls)}
        filtered_d = {k: v for k, v in d.items() if k in field_names}
        
        return cls(**filtered_d)

@dataclass
class GoldenQuestion:
    golden_question_id: str
    exam_year: int
    paper: str
    session: str
    question_number: int

    official_id: Optional[str]
    go_id: Optional[str]

    question_text: str
    options: Dict[str, str]
    marks: float
    question_type: str
    answer: str

    go_subject: Optional[str]
    go_topic: Optional[str]
    go_url: Optional[str]

    match_method: str
    match_score: float
    match_status: MatchStatus
    match_reason: str
    coverage_status: CoverageStatus

    provenance_json: Dict[str, Any]
    reconciliation_run_id: str
    algorithm_version: str
    matching_config_version: str
    created_at: datetime

@dataclass
class SourceRecord:
    filename: str
    source_type: SourceType
    source_url: str
    download_date: datetime
    file_checksum: str
    file_size: int
    year_range: str
    verified: bool

@dataclass
class ExamRecord:
    year: int
    session: str
    total_questions: int
    total_marks: float
    paper_format: str
    era: str
    source_official: bool
    source_go: bool

def generate_question_id(year: int, session: str, question_number: int) -> str:
    """Generate a unique ID for a question."""
    session_str = str(session).upper().strip()
    if not session_str:
        session_str = "NONE"
    try:
        q_num = int(question_number)
        return f"GATE_{year}_{session_str}_{q_num:02d}"
    except (ValueError, TypeError):
        return f"GATE_{year}_{session_str}_{question_number}"

@dataclass
class EnrichmentRecord:
    enrichment_id: str
    golden_question_id: str
    taxonomy_version: str
    validation_status: str
    error_message: Optional[str]
    ai_subject: Optional[str]
    ai_topic: Optional[str]
    ai_subtopic: Optional[str]
    core_concepts: List[Dict[str, Any]]
    difficulty_score: Optional[int]
    difficulty_confidence: Optional[float]
    difficulty_rationale: Optional[str]
    cognitive_level: Optional[str]
    embedding_model: Optional[str]
    embedding_version: Optional[str]
    embedding: Optional[bytes]
    llm_provider: str
    llm_model: str
    llm_prompt_version: str
    enrichment_run_id: str
    created_at: datetime
