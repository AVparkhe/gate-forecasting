import re
import logging
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

class QuestionSegmenter:
    """Shared utilities for segmenting and parsing GATE questions."""
    
    # Regex patterns for detecting question boundaries
    QUESTION_PATTERNS = [
        r'Q\.?\s*(\d+)',           # Q.1, Q 1, Q.01
        r'Question\s+#?(\d+)',     # Question 1, Question #1  
        r'^\s*(\d+)\.\s+',         # 1. (at line start)
        r'^\s*(\d+)\)',            # 1)
    ]
    
    # Patterns for MCQ options
    OPTION_PATTERNS = [
        r'\(([A-D])\)\s*(.+?)(?=\([A-D]\)|$)',  # (A) text
        r'\b([A-D])\)\s*(.+?)(?=[A-D]\)|$)',     # A) text
        r'\b([A-D])\.\s*(.+?)(?=[A-D]\.|$)',     # A. text
    ]
    
    @staticmethod
    def detect_question_boundaries(text: str) -> List[Tuple[int, int, int]]:
        """Find question start positions in text.
        Returns list of (question_number, start_pos, end_pos).
        Tries multiple patterns in priority order.
        """
        boundaries = []
        # Join patterns with OR to capture any matches
        pattern = re.compile('|'.join(QuestionSegmenter.QUESTION_PATTERNS), re.MULTILINE | re.IGNORECASE)
        matches = list(pattern.finditer(text))
        
        for i, match in enumerate(matches):
            # Extract question number, which could be in any of the groups
            q_num_str = next(g for g in match.groups() if g is not None)
            try:
                q_num = int(q_num_str)
            except ValueError:
                continue
                
            start_pos = match.start()
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(text)
            boundaries.append((q_num, start_pos, end_pos))
            
        return boundaries
    
    @staticmethod  
    def extract_options(question_text: str) -> Optional[Dict[str, str]]:
        """Extract MCQ options from question text.
        Returns dict like {"A": "...", "B": "...", "C": "...", "D": "..."} or None for NAT.
        """
        for pattern in QuestionSegmenter.OPTION_PATTERNS:
            regex = re.compile(pattern, re.DOTALL)
            matches = regex.findall(question_text)
            if matches and len(matches) >= 4:
                # We expect at least A, B, C, D
                options = {m[0].upper(): m[1].strip() for m in matches[:4]}
                if set(options.keys()) == {'A', 'B', 'C', 'D'}:
                    return options
        return None
    
    @staticmethod
    def classify_question_type(question_text: str, options: Optional[Dict]) -> str:
        """Classify as MCQ, MSQ, or NAT based on options and text cues.
        - MCQ: has exactly 4 options with single correct
        - MSQ: has options + "one or more" / "multiple" cue
        - NAT: no options, or has NAT/numerical answer cue
        """
        text_lower = question_text.lower()
        if options and len(options) == 4:
            if "one or more" in text_lower or "multiple" in text_lower:
                return "MSQ"
            return "MCQ"
        return "NAT"
    
    @staticmethod
    def detect_marks(question_text: str, question_number: int, total_questions: int = 65) -> int:
        """Detect marks for a question.
        Modern format (65 questions): Q1-25 = 1 mark, Q26-65 = 2 marks
        Check text for explicit marks indicators too.
        """
        # Try explicit mention
        match = re.search(r'(?:Marks?|marks?)\s*[:=]?\s*(\d+)', question_text)
        if match:
            return int(match.group(1))
            
        if total_questions == 65:
            if 1 <= question_number <= 25:
                return 1
            elif 26 <= question_number <= 65:
                return 2
        return 1
    
    @staticmethod
    def clean_question_text(text: str) -> str:
        """Clean extracted question text:
        - Remove page numbers, headers, footers
        - Normalize whitespace
        - Remove GATE paper header text
        - Fix encoding issues
        """
        # Remove page numbers, headers, footers
        text = re.sub(r'Page\s+\d+.*?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'GATE CSE.*?\d{4}', '', text, flags=re.IGNORECASE)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    @staticmethod
    def extract_year_from_text(text: str) -> Optional[int]:
        """Extract GATE year from text like 'GATE CSE 2024' or 'GATE 2024'."""
        match = re.search(r'GATE\s+(?:CSE\s+)?(\d{4})', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
