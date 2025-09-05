from pathlib import Path

import duckdb

# Database connection
DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "data" / "kissaten.duckdb"
conn = duckdb.connect(str(DATABASE_PATH))