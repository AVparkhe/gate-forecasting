import pymupdf as fitz  # PyMuPDF
import logging
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
import string

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PageContent:
    """Extracted content from a single PDF page."""
    page_number: int
    text: str
    has_images: bool
    image_count: int
    text_quality: float  # 0.0-1.0 based on readable char ratio
    width: float
    height: float

@dataclass 
class PDFContent:
    """Complete extracted content from a PDF file."""
    filepath: str
    total_pages: int
    pages: List[PageContent]
    metadata: Dict[str, str]
    avg_text_quality: float
    total_chars: int
    needs_ocr: bool  # True if avg quality < 0.3

class PDFExtractor:
    """Extracts text content from GATE CSE PDF files."""
    
    OCR_THRESHOLD = 0.3  # Below this, recommend OCR
    
    def __init__(self):
        pass
    
    def extract(self, pdf_path: Path) -> PDFContent:
        """Extract all text from a PDF file.
        Uses PyMuPDF (fitz) as primary extractor.
        Computes text quality metrics per page.
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            raise
        
        pages = []
        total_chars = 0
        total_quality = 0.0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            images = page.get_images()
            image_count = len(images)
            
            rect = page.rect
            width = rect.width
            height = rect.height
            
            quality = self._compute_text_quality(text)
            
            page_content = PageContent(
                page_number=page_num,
                text=text,
                has_images=image_count > 0,
                image_count=image_count,
                text_quality=quality,
                width=width,
                height=height
            )
            pages.append(page_content)
            
            total_chars += len(text)
            total_quality += quality
            
        avg_quality = total_quality / len(doc) if len(doc) > 0 else 0.0
        metadata = doc.metadata or {}
        
        doc.close()
        
        return PDFContent(
            filepath=str(pdf_path),
            total_pages=len(pages),
            pages=pages,
            metadata=metadata,
            avg_text_quality=avg_quality,
            total_chars=total_chars,
            needs_ocr=avg_quality < self.OCR_THRESHOLD
        )
    
    def extract_page_range(self, pdf_path: Path, start: int, end: int) -> List[PageContent]:
        """Extract text from specific page range (0-indexed)."""
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            raise
            
        pages = []
        # Ensure bounds
        start = max(0, start)
        end = min(len(doc) - 1, end)
        
        for page_num in range(start, end + 1):
            page = doc[page_num]
            text = page.get_text("text")
            images = page.get_images()
            image_count = len(images)
            
            rect = page.rect
            quality = self._compute_text_quality(text)
            
            page_content = PageContent(
                page_number=page_num,
                text=text,
                has_images=image_count > 0,
                image_count=image_count,
                text_quality=quality,
                width=rect.width,
                height=rect.height
            )
            pages.append(page_content)
            
        doc.close()
        return pages
    
    def _compute_text_quality(self, text: str) -> float:
        """Compute quality score for extracted text.
        - Ratio of alphanumeric + common punctuation to total characters
        - Penalize if text is very short for a full page
        - Returns 0.0 to 1.0
        """
        if not text or len(text) < 50:
            return 0.0
            
        # letters + digits + common punctuation + whitespace
        valid_chars = set(string.ascii_letters + string.digits + string.punctuation + string.whitespace)
        
        valid_count = sum(1 for c in text if c in valid_chars)
        return float(valid_count) / len(text)
    
    def get_full_text(self, pdf_path: Path) -> str:
        """Convenience: return all pages concatenated as single string."""
        content = self.extract(pdf_path)
        return "\n".join(p.text for p in content.pages)
    
    def save_extracted(self, content: PDFContent, output_dir: Path) -> Path:
        """Save extracted content to a JSON file.
        Returns path to saved file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = Path(content.filepath)
        out_file = output_dir / f"{pdf_path.stem}_extracted.json"
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(asdict(content), f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved extracted content to {out_file}")
        return out_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract text from GATE CSE PDF.")
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
    parser.add_argument("--out_dir", type=str, default=".", help="Output directory for JSON")
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        logger.error(f"File not found: {pdf_path}")
        exit(1)
        
    extractor = PDFExtractor()
    logger.info(f"Extracting: {pdf_path}")
    content = extractor.extract(pdf_path)
    
    logger.info(f"Pages: {content.total_pages}")
    logger.info(f"Total Chars: {content.total_chars}")
    logger.info(f"Avg Quality: {content.avg_text_quality:.2f}")
    logger.info(f"Needs OCR: {content.needs_ocr}")
    
    out_dir = Path(args.out_dir)
    extractor.save_extracted(content, out_dir)
