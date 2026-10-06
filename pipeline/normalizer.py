import hashlib
import logging
import re
from typing import List, Dict, Optional, Set
from models.question import StructuredQuestion, ExtractionQuality, SourceType

logger = logging.getLogger(__name__)

class QuestionNormalizer:
    """Normalizes, validates, and deduplicates extracted GATE questions."""
    
    def normalize_all(self, questions: List[StructuredQuestion]) -> List[StructuredQuestion]:
        """Run full normalization pipeline on a list of questions.
        1. Normalize text
        2. Validate completeness
        3. Deduplicate
        4. Compute checksums
        Returns cleaned list.
        """
        logger.info(f"Starting normalization for {len(questions)} questions.")
        
        # 1. Normalize text & compute checksums
        for q in questions:
            q.question_text = self.normalize_text(q.question_text)
            for opt_key, opt_val in q.options.items():
                q.options[opt_key] = self.normalize_text(opt_val)
            q.checksum = self.compute_checksum(q.question_text)
            
        # 2. Validate completeness (we could filter out invalid ones or just log them, here we just keep them but log invalid ones)
        report = self.get_validation_report(questions)
        logger.info(f"Validation report: {report}")
        
        # 3. Deduplicate
        deduped_questions = self.deduplicate(questions)
        logger.info(f"Deduplication removed {len(questions) - len(deduped_questions)} duplicates.")
        
        return deduped_questions
    
    def normalize_text(self, text: str) -> str:
        """Standardize question text:
        - Normalize unicode chars
        - Fix common OCR errors
        - Normalize whitespace (collapse multiple spaces/newlines)
        - Normalize math symbols
        - Strip leading/trailing whitespace
        """
        if not text:
            return ""
        
        # Normalize unicode (replace smart quotes, en/em dashes)
        text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
        text = text.replace('–', '-').replace('—', '-')
        
        # Normalize whitespace (collapse multiple spaces/newlines)
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        return text.strip()
    
    def validate_question(self, q: StructuredQuestion) -> Dict[str, bool]:
        """Validate question completeness. Returns dict of checks:
        - has_text: question_text is non-empty and > 10 chars
        - has_year: year is between 1987 and 2026
        - has_marks: marks is 1 or 2
        - has_type: question_type is valid
        - has_number: question_number > 0
        - text_quality: text doesn't have too many garbage chars
        """
        has_text = bool(q.question_text and len(q.question_text) > 10)
        has_year = bool(q.year and 1987 <= q.year <= 2026)
        has_marks = bool(q.marks in [1, 2, 1.0, 2.0])
        has_type = q.question_type is not None
        has_number = bool(q.question_number and q.question_number > 0)
        
        # simple check for garbage chars (count non-ascii)
        non_ascii_count = sum(1 for char in q.question_text if ord(char) > 127)
        text_quality = (non_ascii_count / len(q.question_text) < 0.1) if q.question_text else False
        
        return {
            "has_text": has_text,
            "has_year": has_year,
            "has_marks": has_marks,
            "has_type": has_type,
            "has_number": has_number,
            "text_quality": text_quality
        }
    
    def deduplicate(self, questions: List[StructuredQuestion]) -> List[StructuredQuestion]:
        """Remove duplicate questions.
        A question is duplicate if it has the same (year, session, question_number).
        When duplicates found, prefer the one with better extraction_quality
        or the one from official source.
        """
        seen: Dict[str, StructuredQuestion] = {}
        
        for q in questions:
            key = f"{q.year}_{q.session}_{q.question_number}"
            
            if key not in seen:
                seen[key] = q
            else:
                existing = seen[key]
                
                # Compare qualities, prefer Official source first
                if q.source == SourceType.OFFICIAL and existing.source != SourceType.OFFICIAL:
                    seen[key] = q
                elif q.source == existing.source:
                    # Prefer higher quality
                    quality_rank = {
                        ExtractionQuality.HIGH: 4,
                        ExtractionQuality.MEDIUM: 3,
                        ExtractionQuality.LOW: 2,
                        ExtractionQuality.FAILED: 1,
                        None: 0
                    }
                    q_rank = quality_rank.get(q.extraction_quality, 0)
                    existing_rank = quality_rank.get(existing.extraction_quality, 0)
                    
                    if q_rank > existing_rank:
                        seen[key] = q

        return list(seen.values())
    
    def compute_checksum(self, text: str) -> str:
        """Compute SHA256 of normalized question text."""
        if not text:
            return ""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def get_validation_report(self, questions: List[StructuredQuestion]) -> Dict:
        """Generate a validation report with stats on issues found."""
        report = {
            "total_questions": len(questions),
            "missing_text": 0,
            "invalid_year": 0,
            "invalid_marks": 0,
            "missing_type": 0,
            "invalid_number": 0,
            "poor_text_quality": 0,
            "fully_valid": 0
        }
        
        for q in questions:
            validity = self.validate_question(q)
            if not validity["has_text"]:
                report["missing_text"] += 1
            if not validity["has_year"]:
                report["invalid_year"] += 1
            if not validity["has_marks"]:
                report["invalid_marks"] += 1
            if not validity["has_type"]:
                report["missing_type"] += 1
            if not validity["has_number"]:
                report["invalid_number"] += 1
            if not validity["text_quality"]:
                report["poor_text_quality"] += 1
                
            if all(validity.values()):
                report["fully_valid"] += 1
                
        return report
