# management functions for collectors/industry
COLLECTORS_DB = [
    {'name':'Pengepul A','types':['Plastik PET','Kertas'],'price_per_kg':5000,'rating':4.5},
    {'name':'Pengepul B','types':['Plastik PET','HDPE'],'price_per_kg':4000,'rating':4.0},
]

def show_profiles():
    import streamlit as st, pandas as pd
    st.table(pd.DataFrame(COLLECTORS_DB))

def get_collector(name):
    for c in COLLECTORS_DB:
        if c['name']==name: return c
    return None
