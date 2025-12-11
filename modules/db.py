import sqlite3, os, pandas as pd
DB='multiwaste.db'

def init_db():
    conn=sqlite3.connect(DB, check_same_thread=False)
    cur=conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, created_at TEXT, household TEXT, address TEXT, material TEXT, weight REAL, status TEXT, collector TEXT, tx_id TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS ledger (tx_id TEXT PRIMARY KEY, created_at TEXT, household TEXT, collector TEXT, material TEXT, weight REAL, price_per_kg REAL, total REAL, verified INTEGER)''')
    conn.commit()
    return conn

conn=init_db()

def add_request(household,address,material,weight):
    cur=conn.cursor()
    cur.execute('INSERT INTO requests (created_at,household,address,material,weight,status) VALUES (datetime("now"),?,?,?,?,?)', (household,address,material,weight,'OPEN'))
    conn.commit()

def get_requests(status='OPEN'):
    return pd.read_sql_query(f"SELECT * FROM requests WHERE status='{status}'", conn)

def add_ledger_entry(entry):
    cur=conn.cursor()
    cur.execute('INSERT OR REPLACE INTO ledger (tx_id,created_at,household,collector,material,weight,price_per_kg,total,verified) VALUES (?,?,?,?,?,?,?,?,?)',(
        entry['tx_id'], entry['created_at'], entry['household'], entry['collector'], entry['material'], entry['weight'], entry['price_per_kg'], entry['total'], entry.get('verified',0)
    ))
    conn.commit()

def get_ledger_df():
    return pd.read_sql_query('SELECT * FROM ledger ORDER BY created_at DESC', conn)
