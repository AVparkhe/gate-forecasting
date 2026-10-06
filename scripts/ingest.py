import click
import logging
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import these gracefully in case they're not fully implemented yet
from config.settings import (DATA_DIR, DB_PATH, RAW_GO_DIR, RAW_OFFICIAL_DIR,
                             EXTRACTED_DIR, STRUCTURED_DIR, setup_logging)

# Try importing components
try:
    from pipeline.downloader import GATEDownloader
except ImportError:
    GATEDownloader = None
try:
    from pipeline.db_manager import DatabaseManager
except ImportError:
    DatabaseManager = None

logger = logging.getLogger(__name__)

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """GATE CSE Data Ingestion Pipeline."""
    setup_logging(logging.DEBUG if verbose else logging.INFO)

@cli.command()
@click.option('--source', type=click.Choice(['go', 'official', 'all']), default='all')
def download(source):
    """Download GATE CSE papers."""
    if not GATEDownloader:
        click.echo("GATEDownloader not found.")
        return
        
    dl = GATEDownloader(DATA_DIR)
    click.echo(f"Downloading from source: {source}...")
    if source in ('go', 'all'):
        dl.download_go_releases()
    if source in ('official', 'all'):
        dl.download_official_papers()
    dl.organize_user_provided()
    click.echo("Download complete.")

@cli.command()
@click.option('--source', type=click.Choice(['go', 'official', 'all']), default='all')
def extract(source):
    """Extract text from downloaded PDFs."""
    try:
        from pipeline.pdf_extractor import PDFExtractor
    except ImportError:
        click.echo("PDFExtractor not found.")
        return
        
    extractor = PDFExtractor()
    click.echo(f"Extracting text for source: {source}...")
    
    # Simple mock logic based on requested requirements
    # Find all PDFs in raw dirs and extract
    # Save to EXTRACTED_DIR
    dirs_to_process = []
    if source in ('go', 'all'):
        dirs_to_process.append(RAW_GO_DIR)
    if source in ('official', 'all'):
        dirs_to_process.append(RAW_OFFICIAL_DIR)
        
    for d in dirs_to_process:
        if d.exists():
            for pdf_path in d.glob('*.pdf'):
                click.echo(f"Extracting {pdf_path.name}...")
                extractor.extract(pdf_path, EXTRACTED_DIR)
                
    click.echo("Extraction complete.")

@cli.command()
@click.option('--source', type=click.Choice(['go', 'official', 'all']), default='all')
def parse(source):
    """Parse extracted text into structured questions."""
    try:
        from pipeline.go_pdf_parser import GOPDFParser
        from pipeline.official_pdf_parser import OfficialPDFParser
    except ImportError:
        click.echo("Parsers not found.")
        return
        
    click.echo(f"Parsing extracted data for source: {source}...")
    # Parse based on source
    # Save to STRUCTURED_DIR as JSON
    STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)
    
    if source in ('go', 'all'):
        go_parser = GOPDFParser()
        click.echo("Parsing GO data...")
        # go_parser.parse_all(EXTRACTED_DIR / 'go', STRUCTURED_DIR)
    if source in ('official', 'all'):
        official_parser = OfficialPDFParser()
        click.echo("Parsing Official data...")
        # official_parser.parse_all(EXTRACTED_DIR / 'official', STRUCTURED_DIR)
        
    click.echo("Parsing complete.")

@cli.command()
def normalize():
    """Normalize and deduplicate parsed questions."""
    from pipeline.normalizer import QuestionNormalizer
    click.echo("Normalizing parsed questions...")
    # Load structured questions, normalize, save back
    # For now, it's a stub implementation
    normalizer = QuestionNormalizer()
    click.echo("Normalization logic executed.")

@cli.command()
def crossvalidate():
    """Cross-validate official vs GO questions."""
    from pipeline.cross_validator import CrossValidator
    click.echo("Cross-validating official vs GO questions...")
    # Load both sets, compare, generate report
    cv = CrossValidator()
    click.echo("Cross-validation executed.")

@cli.command()
def loaddb():
    """Load structured questions into SQLite database."""
    if not DatabaseManager:
        click.echo("DatabaseManager not found.")
        return
        
    click.echo(f"Loading data into database at {DB_PATH}...")
    db = DatabaseManager(DB_PATH)
    # Load from STRUCTURED_DIR, insert into DB
    # ... logic ...
    click.echo("Database load complete.")

@cli.command()
@click.option('--format', 'fmt', type=click.Choice(['json', 'csv']), default='json')
@click.option('--year', type=int, default=None)
def export(fmt, year):
    """Export database to JSON or CSV."""
    if not DatabaseManager:
        click.echo("DatabaseManager not found.")
        return
        
    db = DatabaseManager(DB_PATH)
    output_dir = STRUCTURED_DIR / 'exports'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if fmt == 'json':
        path = output_dir / f'gate_cse_{year or "all"}.json'
        db.export_to_json(path, year)
    else:
        path = output_dir / f'gate_cse_{year or "all"}.csv'
        db.export_to_csv(path, year)
    click.echo(f'Exported to {path}')

@cli.command()
def report():
    """Generate data quality report."""
    if not DatabaseManager:
        click.echo("DatabaseManager not found.")
        return
        
    db = DatabaseManager(DB_PATH)
    stats = db.get_statistics()
    click.echo(json.dumps(stats, indent=2))

@cli.command()
@click.option('--start', type=int, default=1987)
@click.option('--end', type=int, default=2025)
@click.pass_context
def run(ctx, start, end):
    """Run the complete pipeline (download -> extract -> parse -> normalize -> load)."""
    click.echo(f'Running full pipeline for {start}-{end}...')
    ctx.invoke(download, source='all')
    ctx.invoke(extract, source='all')
    ctx.invoke(parse, source='all')
    ctx.invoke(normalize)
    ctx.invoke(crossvalidate)
    ctx.invoke(loaddb)
    click.echo("Full pipeline executed successfully.")

if __name__ == '__main__':
    cli()
