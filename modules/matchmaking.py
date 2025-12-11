# simple matchmaking: static collectors with location and prices
COLLECTORS=[
    {'name':'Pengepul A','lat':-6.9,'lon':107.6,'price_per_kg':5000,'waste_types':['Plastik PET','Kertas']},
    {'name':'Pengepul B','lat':-6.92,'lon':107.58,'price_per_kg':4000,'waste_types':['Plastik PET','HDPE']},
    {'name':'Bank Sampah C','lat':-6.91,'lon':107.59,'price_per_kg':3000,'waste_types':['Kertas','Kaca','Logam']},
]

def find_collectors_for(material):
    # return collectors that accept material, sorted by price asc
    c=[c for c in COLLECTORS if material in c['waste_types']]
    return sorted(c, key=lambda x: x['price_per_kg'])
