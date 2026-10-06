import sqlite3
from pathlib import Path

DB_PATH = 'data/db/gate_forecasting.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    cursor.execute("SELECT * FROM learning_ledger ORDER BY target_year ASC")
    rows = []
    for r in cursor.fetchall():
        d = dict(r)
        d['problem'] = "Overprediction of historically high-frequency topics ignoring gap."
        d['change'] = "Increase importance of recurrence-gap feature."
        future_years = [d['target_year'] + 1, d['target_year'] + 2, d['target_year'] + 3]
        print(d)
        break
except Exception as e:
    import traceback
    traceback.print_exc()

print("success")
