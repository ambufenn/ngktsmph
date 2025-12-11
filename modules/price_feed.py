# Mock price feed; in production connect to APIs or crowdsourced inputs
def get_prices():
    return [{'material':'Plastik PET','price_per_kg':5000},{'material':'Kertas','price_per_kg':3000},{'material':'Logam','price_per_kg':12000}]
