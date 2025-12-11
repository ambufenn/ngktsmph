import streamlit as st
from datetime import datetime
import pandas as pd
import os
from modules import (
    db, models, matchmaking, scheduler, ledger, tokens, chatbot, dashboard, collectors, price_feed, map_ui
)

st.set_page_config(page_title='MultiWaste CPOTL', layout='wide')
st.title('MultiWaste CPOTL — Prototype')

# Simple role selection
role = st.sidebar.selectbox('Role', ['Household', 'Collector', 'Industry', 'Admin'])

# Common actions
if role == 'Household':
    st.header('Household — Upload & Request Pickup')
    with st.form('upload_form'):
        name = st.text_input('Nama kontak')
        address = st.text_area('Alamat')
        uploaded = st.file_uploader('Foto sampah (jpg/png)', type=['jpg','jpeg','png'])
        reported_type = st.selectbox('Jenis (lapor)', models.WASTE_TYPES)
        est_weight = st.number_input('Perkiraan berat (kg)', min_value=0.0, step=0.1)
        submitted = st.form_submit_button('Analisa & Cari Pengepul')
    if submitted:
        photo_path = None
        if uploaded:
            os.makedirs('uploads', exist_ok=True)
            fname = f"uploads/{int(datetime.utcnow().timestamp())}_{uploaded.name}"
            with open(fname, 'wb') as f:
                f.write(uploaded.getbuffer())
            photo_path = fname
        # 1) classify
        classification = models.classify_image(photo_path)
        st.subheader('Hasil Klasifikasi')
        st.json(classification)
        # 2) matchmaking
        candidates = matchmaking.find_collectors_for(classification['label'])
        st.subheader('Pengepul Tersedia')
        st.table(pd.DataFrame(candidates))
        for c in candidates:
            if st.button(f"Request pickup by {c['name']}", key=f"req_{c['name']}"):
                # schedule
                sched = scheduler.create_pickup(name, address, c['name'], classification['label'], est_weight, photo_path)
                # ledger entry
                tx = ledger.record_transaction(
                    household=name, collector=c['name'], material=classification['label'], weight=est_weight, price_per_kg=c['price_per_kg'], photo=photo_path
                )
                # token reward
                tokens.award_tokens(household=name, material=classification['label'], weight=est_weight)
                st.success('Pickup requested and recorded in ledger. TX ID: ' + tx['tx_id'])

elif role == 'Collector':
    st.header('Collector — Daftar Request')
    df = db.get_requests(status='OPEN')
    st.dataframe(df)
    st.write('Collector can accept requests via the Assign button in app logic (stub).')

elif role == 'Industry':
    st.header('Industry / Recycler Dashboard')
    collectors.show_profiles()

else:
    st.header('Admin Dashboard')
    st.subheader('Ledger (recent)')
    st.dataframe(ledger.get_ledger_df())
    st.subheader('Price Feed (mock)')
    st.table(price_feed.get_prices())

# Sidebar quick links
st.sidebar.markdown('---')
st.sidebar.markdown('Features: AI classification, matchmaking, scheduler, ledger (CPOTL), tokens, chatbot, dashboard, price feed, map.')
