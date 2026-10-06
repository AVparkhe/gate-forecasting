import argparse
import sys
import logging
import sqlite3
from pathlib import Path
import json

# Adjust path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DB_PATH

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def generate_embeddings(db_path: Path, model_name: str = 'all-MiniLM-L6-v2'):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("sentence-transformers not installed. Please pip install sentence-transformers torch")
        sys.exit(1)
        
    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # We only embed enriched questions
    cursor.execute("""
        SELECT q.golden_question_id, q.question_text, e.enrichment_id
        FROM golden_questions q
        JOIN question_enrichment e ON q.golden_question_id = e.golden_question_id
        WHERE e.embedding IS NULL
    """)
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("No enriched questions pending embedding generation.")
        conn.close()
        return
        
    logger.info(f"Found {len(rows)} questions to embed.")
    
    batch_size = 32
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        texts = [r['question_text'] for r in batch]
        
        embeddings = model.encode(texts)
        
        # Update DB
        for j, row in enumerate(batch):
            emb_bytes = embeddings[j].tobytes()
            cursor.execute("""
                UPDATE question_enrichment
                SET embedding_model = ?, embedding_version = ?, embedding = ?
                WHERE enrichment_id = ?
            """, (model_name, "v1", emb_bytes, row['enrichment_id']))
            
        conn.commit()
        logger.info(f"Processed batch {i//batch_size + 1}/{(len(rows)-1)//batch_size + 1}")
        
    conn.close()
    logger.info("Embedding generation complete.")

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for enriched questions.")
    parser.add_argument('--model', type=str, default='all-MiniLM-L6-v2', help="Sentence transformer model name")
    
    args = parser.parse_args()
    generate_embeddings(DB_PATH, args.model)
    
if __name__ == "__main__":
    main()
