import logging
import uuid
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher

from models.question import StructuredQuestion, GoldenQuestion, MatchStatus, CoverageStatus, SourceType

logger = logging.getLogger(__name__)

class CrossValidator:
    """
    Implements a 3-stage validation engine for reconciling Official and GATE Overflow datasets.
    """
    
    TEXT_SIMILARITY_THRESHOLD = 0.8
    
    def __init__(self, run_id: str, algo_version: str, config_version: str):
        self.run_id = run_id
        self.algo_version = algo_version
        self.config_version = config_version
    
    def reconcile(self, raw_questions: List[Dict[str, Any]]) -> Tuple[List[GoldenQuestion], Dict[str, Any], List[Dict[str, Any]]]:
        """
        Takes raw dictionaries from the 'questions' table.
        Returns:
            - List of GoldenQuestion objects
            - Report dictionary
            - Review queue (list of dicts)
        """
        official_qs = []
        go_qs = []
        
        for rq in raw_questions:
            q = StructuredQuestion.from_dict(rq)
            # Add year and session dynamically attached from the JOIN query in DB Manager
            q.year = rq.get('year')
            q.session = str(rq.get('session', '1'))
            if getattr(q.source, 'value', str(q.source)) == "OFFICIAL":
                official_qs.append(q)
            else:
                go_qs.append(q)
                
        # Group by candidate keys
        official_dict = self._group_by_key(official_qs)
        go_dict = self._group_by_key(go_qs)
        
        all_keys = set(official_dict.keys()).union(set(go_dict.keys()))
        
        golden_questions = []
        review_queue = []
        report = self._init_report()
        
        for key in all_keys:
            year, session, q_num = key
            q_offs = official_dict.get(key, [])
            q_gos = go_dict.get(key, [])
            
            # Update source coverage stats
            if not q_offs and not q_gos:
                continue
                
            if q_offs and q_gos:
                coverage_status = CoverageStatus.BOTH_SOURCES
            elif q_offs:
                coverage_status = CoverageStatus.GO_SOURCE_MISSING
            else:
                coverage_status = CoverageStatus.OFFICIAL_SOURCE_MISSING
            
            # Handle 1-to-1 matches
            if len(q_offs) == 1 and len(q_gos) == 1:
                q_off = q_offs[0]
                q_go = q_gos[0]
                
                similarity = self._compute_similarity(q_off.question_text, q_go.question_text)
                
                if similarity >= self.TEXT_SIMILARITY_THRESHOLD:
                    status = MatchStatus.AUTO_VERIFIED
                    reason = f"Exact key match. Text similarity = {similarity:.2f}"
                else:
                    status = MatchStatus.REVIEW_REQUIRED
                    reason = f"Exact key match but text similarity is low ({similarity:.2f})"
                    
                gq = self._create_golden_question(q_off, q_go, status, reason, coverage_status, similarity)
                golden_questions.append(gq)
                self._update_report(report, year, status, coverage_status)
                
                if status == MatchStatus.REVIEW_REQUIRED:
                    review_queue.append(self._create_review_item(q_off, q_go, similarity, reason))
                    
            # Handle Official Only
            elif len(q_offs) == 1 and len(q_gos) == 0:
                q_off = q_offs[0]
                status = MatchStatus.UNMATCHED_OFFICIAL
                reason = "No GO candidate found for this year/session/q_num"
                gq = self._create_golden_question(q_off, None, status, reason, coverage_status, 0.0)
                golden_questions.append(gq)
                self._update_report(report, year, status, coverage_status)
                
            # Handle GO Only
            elif len(q_offs) == 0 and len(q_gos) == 1:
                q_go = q_gos[0]
                status = MatchStatus.GO_ONLY
                reason = "No Official candidate found for this year/session/q_num"
                gq = self._create_golden_question(None, q_go, status, reason, coverage_status, 0.0)
                golden_questions.append(gq)
                self._update_report(report, year, status, coverage_status)
                
            # Handle duplicates (e.g., multiple questions for the same number)
            else:
                # We have multiple candidates. We'll add them to review queue and mark DUPLICATE_CANDIDATE
                status = MatchStatus.DUPLICATE_CANDIDATE
                reason = f"Multiple candidates found: {len(q_offs)} Official, {len(q_gos)} GO"
                
                # We just create a dummy gq for the first one for completeness, but flag strongly for review
                q_off = q_offs[0] if q_offs else None
                q_go = q_gos[0] if q_gos else None
                
                gq = self._create_golden_question(q_off, q_go, status, reason, coverage_status, 0.0)
                golden_questions.append(gq)
                self._update_report(report, year, status, coverage_status)
                
                review_queue.append(self._create_review_item(q_off, q_go, 0.0, reason))
                
        return golden_questions, report, review_queue

    def _group_by_key(self, questions: List[StructuredQuestion]) -> Dict[Tuple[int, str, int], List[StructuredQuestion]]:
        grouped = {}
        for q in questions:
            key = (q.year, q.session, q.question_number)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(q)
        return grouped
        
    def _compute_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
    def _create_golden_question(self, q_off: Optional[StructuredQuestion], q_go: Optional[StructuredQuestion], 
                                status: MatchStatus, reason: str, cov_status: CoverageStatus, sim: float) -> GoldenQuestion:
        
        base_q = q_off if q_off else q_go
        
        # Provenance explicitly traces each field
        provenance = {
            "question_text": {"source": "official" if q_off else "gateoverflow", "source_id": q_off.id if q_off else q_go.id},
            "options": {"source": "official" if q_off else "gateoverflow", "source_id": q_off.id if q_off else q_go.id},
            "marks": {"source": "official" if q_off else "gateoverflow", "source_id": q_off.id if q_off else q_go.id},
            "answer": {"source": "official" if q_off else "gateoverflow", "source_id": q_off.id if q_off else q_go.id},
        }
        
        if q_go and (q_go.go_subject or q_go.go_topic):
            provenance["subject"] = {"source": "gateoverflow", "source_id": q_go.id}
            provenance["topic"] = {"source": "gateoverflow", "source_id": q_go.id}

        q_type_val = base_q.question_type.value if hasattr(base_q.question_type, 'value') else str(base_q.question_type)

        return GoldenQuestion(
            golden_question_id=str(uuid.uuid4()),
            exam_year=base_q.year,
            paper="CS",  # Defaulting to CS
            session=base_q.session,
            question_number=base_q.question_number,
            official_id=q_off.id if q_off else None,
            go_id=q_go.id if q_go else None,
            question_text=base_q.question_text,
            options=base_q.options,
            marks=base_q.marks,
            question_type=q_type_val,
            answer=base_q.correct_answer,
            go_subject=q_go.go_subject if q_go else None,
            go_topic=q_go.go_topic if q_go else None,
            go_url=q_go.go_url if q_go else None,
            match_method="exact_key_and_text",
            match_score=sim,
            match_status=status,
            match_reason=reason,
            coverage_status=cov_status,
            provenance_json=provenance,
            reconciliation_run_id=self.run_id,
            algorithm_version=self.algo_version,
            matching_config_version=self.config_version,
            created_at=datetime.now()
        )
        
    def _create_review_item(self, q_off: Optional[StructuredQuestion], q_go: Optional[StructuredQuestion], sim: float, reason: str) -> Dict[str, Any]:
        return {
            "year": q_off.year if q_off else q_go.year,
            "session": q_off.session if q_off else q_go.session,
            "question_number": q_off.question_number if q_off else q_go.question_number,
            "official_text": q_off.question_text if q_off else None,
            "go_text": q_go.question_text if q_go else None,
            "similarity_score": sim,
            "match_reason": reason,
            "official_id": q_off.id if q_off else None,
            "go_id": q_go.id if q_go else None
        }
        
    def _init_report(self) -> Dict[str, Any]:
        return {
            "total_processed": 0,
            "match_status": {
                "AUTO_VERIFIED": 0,
                "REVIEW_REQUIRED": 0,
                "UNMATCHED_OFFICIAL": 0,
                "GO_ONLY": 0,
                "DUPLICATE_CANDIDATE": 0
            },
            "coverage_status": {
                "BOTH_SOURCES": 0,
                "OFFICIAL_ONLY": 0,
                "GO_ONLY": 0,
                "OFFICIAL_SOURCE_MISSING": 0,
                "GO_SOURCE_MISSING": 0
            },
            "per_year": {}
        }
        
    def _update_report(self, report: Dict[str, Any], year: int, status: MatchStatus, cov_status: CoverageStatus):
        report["total_processed"] += 1
        
        status_name = status.value if hasattr(status, 'value') else str(status)
        cov_name = cov_status.value if hasattr(cov_status, 'value') else str(cov_status)
        
        if status_name in report["match_status"]:
            report["match_status"][status_name] += 1
        if cov_name in report["coverage_status"]:
            report["coverage_status"][cov_name] += 1
            
        if year not in report["per_year"]:
            report["per_year"][year] = {
                "AUTO_VERIFIED": 0,
                "REVIEW_REQUIRED": 0,
                "UNMATCHED_OFFICIAL": 0,
                "GO_ONLY": 0,
                "DUPLICATE_CANDIDATE": 0
            }
        
        if status_name in report["per_year"][year]:
            report["per_year"][year][status_name] += 1
