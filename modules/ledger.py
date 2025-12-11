# CPOTL ledger: append-only with hash-based tx_id
import hashlib, json, datetime
from . import db

def record_transaction(household, collector, material, weight, price_per_kg, photo=None):
    now = datetime.datetime.utcnow().isoformat()
    total = weight * price_per_kg
    payload = {'household':household,'collector':collector,'material':material,'weight':weight,'price_per_kg':price_per_kg,'total':total,'created_at':now}
    raw = json.dumps(payload, sort_keys=True).encode('utf-8')
    tx_hash = hashlib.sha256(raw).hexdigest()
    entry = {'tx_id':tx_hash, 'created_at':now, 'household':household, 'collector':collector, 'material':material, 'weight':weight, 'price_per_kg':price_per_kg, 'total':total, 'verified':0}
    db.add_ledger_entry(entry)
    return entry

def get_ledger_df():
    return db.get_ledger_df()
