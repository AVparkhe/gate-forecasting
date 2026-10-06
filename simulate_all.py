import sqlite3
import subprocess
import os

DB_PATH = 'data/db/gate_forecasting.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT exam_year, count(*) as c FROM golden_questions GROUP BY exam_year HAVING c > 10 ORDER BY exam_year ASC")
    years = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"Found {len(years)} years with enough data: {years}")
    
    for y in years:
        print(f"--- Simulating year {y} ---")
        subprocess.run(["python3", "scripts/forecast_runner.py", "--year", str(y)])

if __name__ == '__main__':
    main()
