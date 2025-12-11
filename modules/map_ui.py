# Simple map UI using streamlit's built-in map (lat/lon of collectors)
import streamlit as st, pandas as pd
def show_collectors_map(collectors):
    df = pd.DataFrame([{'lat':c.get('lat'), 'lon':c.get('lon'), 'name':c.get('name')} for c in collectors])
    st.map(df)
