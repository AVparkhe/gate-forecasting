import re
import logging
import pymupdf as fitz  # PyMuPDF
from pathlib import Path  
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from models.question import StructuredQuestion, QuestionType, SourceType, ExtractionQuality
from models.question import generate_question_id
from pipeline.question_segmenter import QuestionSegmenter
import hashlib

logger = logging.getLogger(__name__)

class GOPDFParser:
    """Parser for GATE Overflow compilation PDFs."""
    
    # Pattern to match the header: "Group Theory: GATE CSE 1994 | Question: 1.10" or similar
    HEADER_PATTERN = re.compile(r'(.*?):\s*GATE\s*(?:CSE\s*)?(\d{4})\s*\|\s*(?:Question|Q):?\s*([\d\.]+)', re.IGNORECASE)
    
    # Pattern to match metadata tags like: "gate1993 set-theory&algebra group-theory normal descriptive"
    TAGS_PATTERN = re.compile(r'gate(\d{4})\s+([a-zA-Z0-9\-&]+(?:\s+[a-zA-Z0-9\-&]+)*)')
    
    GO_URL_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?gateoverflow\.in/\d+')
    
    def __init__(self):
        self.segmenter = QuestionSegmenter()
    
    def parse_pdf(self, pdf_path: Path) -> List[StructuredQuestion]:
        """Parse a complete GO PDF and extract all questions."""
        questions = []
        try:
            doc = fitz.open(str(pdf_path))
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()
            
            # GO PDFs separate questions/solutions with "Answer key☟"
            chunks = full_text.split("Answer key☟")
            
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                    
                q = self._parse_single_question(chunk, str(pdf_path))
                if q:
                    questions.append(q)
                
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {e}")
            
        return questions
    
    def _parse_single_question(self, text_block: str, source_file: str) -> Optional[StructuredQuestion]:
        """Parse a single question chunk into a StructuredQuestion."""
        year = None
        q_num_str = None
        subject = None
        topic = None
        
        # Try finding header
        header_match = self.HEADER_PATTERN.search(text_block)
        if header_match:
            subject = header_match.group(1).strip()
            year = int(header_match.group(2))
            q_num_str = header_match.group(3)
            # Remove anything before the header match
            text_block = text_block[header_match.start():]
        else:
            # Try finding tags
            tags_match = self.TAGS_PATTERN.search(text_block)
            if tags_match:
                year = int(tags_match.group(1))
                tags = tags_match.group(2).split()
                if len(tags) > 0:
                    subject = tags[0]
                if len(tags) > 1:
                    topic = tags[1]
                # Remove anything before the tags match
                text_block = text_block[tags_match.start():]
        
        if not year:
            return None
            
        # Parse question number (it might be "1.10" or "4", just use a running number or parse float)
        q_num = 0
        if q_num_str:
            try:
                if '.' in q_num_str:
                    q_num = int(q_num_str.split('.')[-1])
                else:
                    q_num = int(q_num_str)
            except ValueError:
                q_num = hash(q_num_str) % 1000 # Fallback
        
        raw_text = self.segmenter.clean_question_text(text_block)
        options = self.segmenter.extract_options(raw_text)
        
        q_type_str = self.segmenter.classify_question_type(raw_text, options)
        if q_type_str == "MCQ":
            q_type = QuestionType.MCQ
        elif q_type_str == "MSQ":
            q_type = QuestionType.MSQ
        else:
            q_type = QuestionType.NAT
            
        marks = self.segmenter.detect_marks(raw_text, q_num)
        
        url_match = self.GO_URL_PATTERN.search(text_block)
        url = url_match.group(0) if url_match else None
        
        checksum = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
        
        return StructuredQuestion(
            id=generate_question_id(year, "1", q_num),
            year=year,
            session="1",
            question_number=q_num,
            question_text=raw_text,
            options=options or {},
            question_type=q_type,
            marks=float(marks),
            correct_answer="",
            source=SourceType.GATEOVERFLOW,
            source_url=url or "",
            source_file=Path(source_file).name,
            extraction_date=datetime.now(),
            raw_text=raw_text,
            checksum=checksum,
            go_subject=subject,
            go_topic=topic,
            go_url=url,
            extraction_quality=ExtractionQuality.MEDIUM,
            extraction_notes=None
        )
