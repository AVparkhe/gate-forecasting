import re
import logging 
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import hashlib
import pymupdf as fitz  # PyMuPDF

from models.question import StructuredQuestion, QuestionType, SourceType, ExtractionQuality
from models.question import generate_question_id
from pipeline.question_segmenter import QuestionSegmenter

logger = logging.getLogger(__name__)

class OfficialPDFParser:
    """Parser for official GATE CSE question papers.
    
    Official papers are sequential: questions numbered 1-65,
    with Q1-25 being 1-mark and Q26-65 being 2-mark (modern format).
    """
    
    def __init__(self):
        self.segmenter = QuestionSegmenter()
    
    def parse_paper(self, pdf_path: Path, year: int, 
                     session: str = "1") -> List[StructuredQuestion]:
        """Parse an official GATE CS paper.
        
        Args:
            pdf_path: Path to the official PDF
            year: Exam year
            session: Session number ("1", "2", or "single")
            
        Returns:
            List of extracted StructuredQuestion objects
        """
        questions = []
        try:
            doc = fitz.open(str(pdf_path))
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            
            boundaries = self.segmenter.detect_question_boundaries(full_text)
            
            for q_num, start_pos, end_pos in boundaries:
                q_text = full_text[start_pos:end_pos].strip()
                cleaned_text = self.segmenter.clean_question_text(q_text)
                options = self.segmenter.extract_options(cleaned_text)
                
                q_type_str = self.segmenter.classify_question_type(cleaned_text, options)
                if q_type_str == "MCQ":
                    q_type = QuestionType.MCQ
                elif q_type_str == "MSQ":
                    q_type = QuestionType.MSQ
                else:
                    q_type = QuestionType.NAT
                    
                marks = self.segmenter.detect_marks(cleaned_text, q_num)
                checksum = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()
                
                q = StructuredQuestion(
                    id=generate_question_id(year, session, q_num),
                    year=year,
                    session=session,
                    question_number=q_num,
                    question_text=cleaned_text,
                    options=options or {},
                    question_type=q_type,
                    marks=float(marks),
                    correct_answer="",
                    source=SourceType.OFFICIAL,
                    source_url="",
                    source_file=Path(pdf_path).name,
                    extraction_date=datetime.now(),
                    raw_text=q_text,
                    checksum=checksum,
                    go_subject=None,
                    go_topic=None,
                    go_url=None,
                    extraction_quality=ExtractionQuality.HIGH,
                    extraction_notes=None
                )
                questions.append(q)
                
            doc.close()
        except Exception as e:
            logger.error(f"Error parsing official paper {pdf_path}: {e}")
            
        return questions
    
    def parse_answer_key(self, key_path: Path) -> Dict[int, str]:
        """Parse an official answer key PDF.
        Returns dict mapping question_number -> answer.
        """
        answers = {}
        try:
            doc = fitz.open(str(key_path))
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
                
            # Naive parsing for answer keys: assuming Q_NUM followed by ANSWER
            pattern = re.compile(r'(\d+)\s+([A-D]|(?:\d+(?:\.\d+)?(?:\s*to\s*\d+(?:\.\d+)?)?))')
            matches = pattern.findall(full_text)
            for q_num, ans in matches:
                answers[int(q_num)] = ans.strip()
                
            doc.close()
        except Exception as e:
            logger.error(f"Error parsing answer key {key_path}: {e}")
            
        return answers
    
    def _detect_paper_format(self, year: int) -> Dict:
        """Detect paper format based on year.
        Returns format info: total_questions, marks_scheme, has_sessions, etc.
        """
        format_info = {
            "total_questions": 65,
            "has_sessions": year in [2014, 2015, 2016, 2021], # Approximate list
            "marks_scheme": "1-25(1m), 26-65(2m)"
        }
        if year < 2014:
            format_info["has_sessions"] = False
        return format_info
