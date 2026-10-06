import sqlite3
import json
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from contextlib import contextmanager

from models.question import ExamRecord, StructuredQuestion, GoldenQuestion, MatchStatus, CoverageStatus

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for GATE data ingestion pipeline."""

    def __init__(self, db_path: Path):
        """
        Initialize the DatabaseManager.
        
        Args:
            db_path (Path): Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_tables(self) -> None:
        """Create database tables and indexes if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # exams table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY,
                year INTEGER,
                session INTEGER,
                total_questions INTEGER,
                total_marks INTEGER,
                paper_format TEXT,
                era TEXT,
                source_official BOOLEAN,
                source_go BOOLEAN
            )
            """)
            
            # questions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                exam_id INTEGER,
                question_number INTEGER,
                question_text TEXT,
                options_json TEXT,
                question_type TEXT,
                marks INTEGER,
                correct_answer TEXT,
                raw_text TEXT,
                text_checksum TEXT,
                source_official BOOLEAN,
                source_go BOOLEAN,
                source_verified BOOLEAN,
                go_subject TEXT,
                go_topic TEXT,
                go_url TEXT,
                extraction_quality REAL,
                extraction_notes TEXT,
                created_at TEXT,
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            )
            """)
            
            # source_provenance table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                source_type TEXT,
                source_url TEXT,
                download_date TEXT,
                file_checksum TEXT,
                file_size INTEGER,
                year_range TEXT,
                verified BOOLEAN
            )
            """)
            
            # answer_keys table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS answer_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER,
                question_number INTEGER,
                answer TEXT,
                source TEXT,
                source_url TEXT,
                FOREIGN KEY (exam_id) REFERENCES exams (id)
            )
            """)
            
            # golden_questions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS golden_questions (
                golden_question_id TEXT PRIMARY KEY,
                exam_year INTEGER,
                paper TEXT,
                session TEXT,
                question_number INTEGER,
                official_id TEXT,
                go_id TEXT,
                question_text TEXT,
                options_json TEXT,
                marks REAL,
                question_type TEXT,
                answer TEXT,
                go_subject TEXT,
                go_topic TEXT,
                go_url TEXT,
                match_method TEXT,
                match_score REAL,
                match_status TEXT,
                match_reason TEXT,
                coverage_status TEXT,
                provenance_json TEXT,
                reconciliation_run_id TEXT,
                algorithm_version TEXT,
                matching_config_version TEXT,
                created_at TEXT
            )
            """)
            
            # question_enrichment table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_enrichment (
                enrichment_id TEXT PRIMARY KEY,
                golden_question_id TEXT UNIQUE,
                taxonomy_version TEXT,
                validation_status TEXT,
                error_message TEXT,
                ai_subject TEXT,
                ai_topic TEXT,
                ai_subtopic TEXT,
                core_concepts TEXT,
                difficulty_score INTEGER,
                difficulty_confidence REAL,
                difficulty_rationale TEXT,
                cognitive_level TEXT,
                embedding_model TEXT,
                embedding_version TEXT,
                embedding BLOB,
                llm_provider TEXT,
                llm_model TEXT,
                llm_prompt_version TEXT,
                enrichment_run_id TEXT,
                created_at TEXT,
                FOREIGN KEY (golden_question_id) REFERENCES golden_questions (golden_question_id)
            )
            """)
            
            # forecast_predictions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS forecast_predictions (
                prediction_id TEXT PRIMARY KEY,
                run_id TEXT,
                target_year INTEGER,
                level TEXT,
                entity_name TEXT,
                predicted_probability REAL,
                predicted_question_count REAL,
                predicted_marks REAL,
                predicted_rank INTEGER,
                confidence_tier TEXT,
                model_name TEXT,
                model_version TEXT,
                feature_version TEXT,
                training_start_year INTEGER,
                training_end_year INTEGER,
                actual_appearance BOOLEAN,
                actual_question_count INTEGER,
                actual_marks REAL,
                error_type TEXT,
                error_reason TEXT
            )
            """)
            
            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_exam_year ON exams(year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_type ON questions(question_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_marks ON questions(marks)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_subject ON questions(go_subject)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gq_year ON golden_questions(exam_year)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_gq_subject ON golden_questions(go_subject)")
            
            conn.commit()
            logger.info("Database tables and indexes verified/created.")

    def insert_exam(self, exam: ExamRecord) -> int:
        """
        Insert an exam record into the database.
        
        Args:
            exam (ExamRecord): The exam to insert.
            
        Returns:
            int: The ID of the inserted exam.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO exams (id, year, session, total_questions, total_marks, paper_format, era, source_official, source_go)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                year=excluded.year,
                session=excluded.session,
                total_questions=excluded.total_questions,
                total_marks=excluded.total_marks,
                paper_format=excluded.paper_format,
                era=excluded.era,
                source_official=excluded.source_official,
                source_go=excluded.source_go
            """, (exam.id, exam.year, exam.session, exam.total_questions, exam.total_marks, exam.paper_format, exam.era, exam.source_official, exam.source_go))
            conn.commit()
            return cursor.lastrowid or exam.id

    def insert_question(self, question: StructuredQuestion, exam_id: int) -> None:
        """
        Insert a question record with upsert logic.
        
        Args:
            question (StructuredQuestion): The question to insert.
            exam_id (int): Foreign key to the exams table.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Serialize fields
            options_json = json.dumps(question.options) if question.options else "{}"
            q_type = question.question_type.value if hasattr(question.question_type, 'value') else str(question.question_type)
            
            # Determine source flags
            source_official = (question.source.value == "OFFICIAL") if hasattr(question.source, 'value') else (str(question.source) == "OFFICIAL")
            source_go = not source_official
            source_verified = False # By default, wait for cross-validation
            
            ext_quality = question.extraction_quality.value if hasattr(question.extraction_quality, 'value') else str(question.extraction_quality) if question.extraction_quality else None
            created_at = question.extraction_date.isoformat() if hasattr(question.extraction_date, 'isoformat') else str(question.extraction_date)
            
            cursor.execute("""
            INSERT INTO questions (
                id, exam_id, question_number, question_text, options_json, question_type, marks, 
                correct_answer, raw_text, text_checksum, source_official, source_go, source_verified, 
                go_subject, go_topic, go_url, extraction_quality, extraction_notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                exam_id=excluded.exam_id,
                question_number=excluded.question_number,
                question_text=excluded.question_text,
                options_json=excluded.options_json,
                question_type=excluded.question_type,
                marks=excluded.marks,
                correct_answer=excluded.correct_answer,
                raw_text=excluded.raw_text,
                text_checksum=excluded.text_checksum,
                source_official=excluded.source_official,
                source_go=excluded.source_go,
                source_verified=excluded.source_verified,
                go_subject=excluded.go_subject,
                go_topic=excluded.go_topic,
                go_url=excluded.go_url,
                extraction_quality=excluded.extraction_quality,
                extraction_notes=excluded.extraction_notes
            """, (
                question.id, exam_id, question.question_number, question.question_text, 
                options_json, q_type, question.marks, question.correct_answer, 
                question.raw_text, question.checksum, source_official, source_go, 
                source_verified, question.go_subject, question.go_topic, question.go_url, 
                ext_quality, question.extraction_notes, created_at
            ))
            conn.commit()

    def insert_answer_key(self, exam_id: int, question_number: int, answer: str, source: str, source_url: str) -> None:
        """
        Insert an answer key record.
        
        Args:
            exam_id (int): Foreign key to the exams table.
            question_number (int): The question number.
            answer (str): The answer key value.
            source (str): Source of the answer key.
            source_url (str): URL of the source.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO answer_keys (exam_id, question_number, answer, source, source_url)
            VALUES (?, ?, ?, ?, ?)
            """, (exam_id, question_number, answer, source, source_url))
            conn.commit()

    def insert_golden_question(self, gq: GoldenQuestion) -> None:
        """Insert a golden question record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            options_json = json.dumps(gq.options) if gq.options else "{}"
            provenance_json = json.dumps(gq.provenance_json) if gq.provenance_json else "{}"
            match_status = gq.match_status.value if hasattr(gq.match_status, 'value') else str(gq.match_status)
            coverage_status = gq.coverage_status.value if hasattr(gq.coverage_status, 'value') else str(gq.coverage_status)
            created_at = gq.created_at.isoformat() if hasattr(gq.created_at, 'isoformat') else str(gq.created_at)

            cursor.execute("""
            INSERT INTO golden_questions (
                golden_question_id, exam_year, paper, session, question_number,
                official_id, go_id, question_text, options_json, marks, question_type, answer,
                go_subject, go_topic, go_url, match_method, match_score, match_status,
                match_reason, coverage_status, provenance_json, reconciliation_run_id,
                algorithm_version, matching_config_version, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(golden_question_id) DO UPDATE SET
                exam_year=excluded.exam_year,
                paper=excluded.paper,
                session=excluded.session,
                question_number=excluded.question_number,
                official_id=excluded.official_id,
                go_id=excluded.go_id,
                question_text=excluded.question_text,
                options_json=excluded.options_json,
                marks=excluded.marks,
                question_type=excluded.question_type,
                answer=excluded.answer,
                go_subject=excluded.go_subject,
                go_topic=excluded.go_topic,
                go_url=excluded.go_url,
                match_method=excluded.match_method,
                match_score=excluded.match_score,
                match_status=excluded.match_status,
                match_reason=excluded.match_reason,
                coverage_status=excluded.coverage_status,
                provenance_json=excluded.provenance_json,
                reconciliation_run_id=excluded.reconciliation_run_id,
                algorithm_version=excluded.algorithm_version,
                matching_config_version=excluded.matching_config_version
            """, (
                gq.golden_question_id, gq.exam_year, gq.paper, gq.session, gq.question_number,
                gq.official_id, gq.go_id, gq.question_text, options_json, gq.marks, gq.question_type, gq.answer,
                gq.go_subject, gq.go_topic, gq.go_url, gq.match_method, gq.match_score, match_status,
                gq.match_reason, coverage_status, provenance_json, gq.reconciliation_run_id,
                gq.algorithm_version, gq.matching_config_version, created_at
            ))
            conn.commit()

    def get_all_questions(self) -> List[Dict[str, Any]]:
        """
        Get all questions and parse year/session from ID.
        
        Returns:
            List[Dict[str, Any]]: List of question dictionaries including year and session.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions")
            
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                d['options'] = json.loads(d['options_json']) if d.get('options_json') else {}
                
                # Parse year and session from ID: GATE_{year}_{session}_{q_num}
                parts = d['id'].split('_')
                if len(parts) >= 4:
                    try:
                        d['year'] = int(parts[1])
                    except ValueError:
                        d['year'] = 0
                    d['session'] = parts[2]
                else:
                    d['year'] = 0
                    d['session'] = "NONE"
                    
                # Fix source field
                if d.get('source_official'):
                    d['source'] = 'OFFICIAL'
                else:
                    d['source'] = 'GATEOVERFLOW'
                    
                # Fix extraction_date if missing
                if 'created_at' in d:
                    d['extraction_date'] = d['created_at']
                    
                if 'text_checksum' in d:
                    d['checksum'] = d['text_checksum']
                else:
                    d['checksum'] = ''
                    
                d['source_url'] = d.get('go_url') or ''
                d['source_file'] = ''
                    
                results.append(d)
            return results

    def get_questions_by_year(self, year: int) -> List[Dict[str, Any]]:
        """
        Get all questions for a specific year.
        
        Args:
            year (int): The exam year.
            
        Returns:
            List[Dict[str, Any]]: List of question dictionaries.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT q.* FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.year = ?
            ORDER BY e.session, q.question_number
            """, (year,))
            return [dict(row) for row in cursor.fetchall()]

    def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific question by ID.
        
        Args:
            question_id (str): The primary key ID of the question.
            
        Returns:
            Optional[Dict[str, Any]]: The question dictionary or None.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_years(self) -> List[int]:
        """
        Get a list of all unique years in the exams table.
        
        Returns:
            List[int]: List of years.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT year FROM exams ORDER BY year")
            return [row['year'] for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics of the dataset.
        
        Returns:
            Dict[str, Any]: Statistics including counts per year, subject, and type.
        """
        stats = {
            "counts_per_year": {},
            "counts_per_subject": {},
            "counts_per_type": {}
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Per year
            cursor.execute("""
            SELECT e.year, COUNT(q.id) as count 
            FROM exams e 
            LEFT JOIN questions q ON e.id = q.exam_id 
            GROUP BY e.year
            """)
            for row in cursor.fetchall():
                if row['year'] is not None:
                    stats["counts_per_year"][row['year']] = row['count']
                
            # Per subject
            cursor.execute("SELECT go_subject, COUNT(id) as count FROM questions GROUP BY go_subject")
            for row in cursor.fetchall():
                subj = row['go_subject'] or 'Unknown'
                stats["counts_per_subject"][subj] = row['count']
                
            # Per type
            cursor.execute("SELECT question_type, COUNT(id) as count FROM questions GROUP BY question_type")
            for row in cursor.fetchall():
                qtype = row['question_type'] or 'Unknown'
                stats["counts_per_type"][qtype] = row['count']
                
        return stats

    def export_to_json(self, output_path: Path, year: Optional[int] = None) -> None:
        """
        Export questions to a JSON file.
        
        Args:
            output_path (Path): Destination JSON file path.
            year (Optional[int]): Filter by year if provided.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if year:
                cursor.execute("""
                SELECT q.* FROM questions q
                JOIN exams e ON q.exam_id = e.id
                WHERE e.year = ?
                """, (year,))
            else:
                cursor.execute("SELECT * FROM questions")
                
            data = [dict(row) for row in cursor.fetchall()]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Exported {len(data)} records to JSON at {output_path}")

    def export_golden_questions(self, output_dir: Path) -> None:
        """
        Export golden questions to JSON.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM golden_questions")
            
            rows = cursor.fetchall()
            data = []
            for row in rows:
                d = dict(row)
                d['options_json'] = json.loads(d['options_json']) if d.get('options_json') else {}
                d['provenance_json'] = json.loads(d['provenance_json']) if d.get('provenance_json') else {}
                data.append(d)
                
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # JSON Export
            json_path = output_dir / "golden_questions.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Exported {len(data)} Golden Questions to JSON at {json_path}")
            
            # Try Parquet Export
            try:
                import pandas as pd
                df = pd.DataFrame(data)
                # Convert dicts to JSON strings for Parquet compatibility if needed, or leave as dicts depending on engine
                df['options_json'] = df['options_json'].apply(json.dumps)
                df['provenance_json'] = df['provenance_json'].apply(json.dumps)
                
                parquet_path = output_dir / "golden_questions.parquet"
                df.to_parquet(parquet_path, engine='pyarrow')
                logger.info(f"Exported {len(data)} Golden Questions to Parquet at {parquet_path}")
            except ImportError:
                logger.info("Pandas/PyArrow not installed. Skipping Parquet export.")

    def insert_enrichment(self, record: 'EnrichmentRecord') -> None:
        """
        Insert an enrichment record. Updates on conflict by golden_question_id.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            core_concepts_json = json.dumps(record.core_concepts) if record.core_concepts else "[]"
            created_at = record.created_at.isoformat() if hasattr(record.created_at, 'isoformat') else str(record.created_at)
            
            cursor.execute("""
            INSERT INTO question_enrichment (
                enrichment_id, golden_question_id, taxonomy_version, validation_status, error_message,
                ai_subject, ai_topic, ai_subtopic, core_concepts, difficulty_score, difficulty_confidence,
                difficulty_rationale, cognitive_level, embedding_model, embedding_version, embedding,
                llm_provider, llm_model, llm_prompt_version, enrichment_run_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(golden_question_id) DO UPDATE SET
                enrichment_id=excluded.enrichment_id,
                taxonomy_version=excluded.taxonomy_version,
                validation_status=excluded.validation_status,
                error_message=excluded.error_message,
                ai_subject=excluded.ai_subject,
                ai_topic=excluded.ai_topic,
                ai_subtopic=excluded.ai_subtopic,
                core_concepts=excluded.core_concepts,
                difficulty_score=excluded.difficulty_score,
                difficulty_confidence=excluded.difficulty_confidence,
                difficulty_rationale=excluded.difficulty_rationale,
                cognitive_level=excluded.cognitive_level,
                embedding_model=excluded.embedding_model,
                embedding_version=excluded.embedding_version,
                embedding=excluded.embedding,
                llm_provider=excluded.llm_provider,
                llm_model=excluded.llm_model,
                llm_prompt_version=excluded.llm_prompt_version,
                enrichment_run_id=excluded.enrichment_run_id,
                created_at=excluded.created_at
            """, (
                record.enrichment_id, record.golden_question_id, record.taxonomy_version, record.validation_status,
                record.error_message, record.ai_subject, record.ai_topic, record.ai_subtopic, core_concepts_json,
                record.difficulty_score, record.difficulty_confidence, record.difficulty_rationale,
                record.cognitive_level, record.embedding_model, record.embedding_version, record.embedding,
                record.llm_provider, record.llm_model, record.llm_prompt_version, record.enrichment_run_id, created_at
            ))
            conn.commit()

    def get_enrichment(self, golden_question_id: str) -> Optional[Dict[str, Any]]:
        """Get an enrichment record by golden_question_id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM question_enrichment WHERE golden_question_id = ?", (golden_question_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d['core_concepts'] = json.loads(d['core_concepts']) if d.get('core_concepts') else []
                return d
            return None
