"""
Streamlit app: Direct Waste Link (DWL) - Prototype with Gemini (optional)
File: streamlit_direct_waste_app.py

Summary:
- Single-file Streamlit prototype for households to create pickup requests and for collectors to accept them.
- Optional integration with Google Gemini (via Google Gen AI Python SDK) to *auto-classify* uploaded waste photos and suggest waste type / contamination level.
- SQLite backend for local testing; easy to push to GitHub and deploy to Streamlit Cloud.

How to run locally:
1. Create a Python virtual env.
2. pip install -r requirements.txt
3. Set environment variables for Gemini (see below) OR skip and the app will work without model.
4. streamlit run streamlit_direct_waste_app.py

Required environment variables for Gemini integration (optional):
- GEMINI_API_KEY (or set GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file path) -- app will try both.
- GEMINI_MODEL (optional) e.g. "gemini-1.5" or leave blank to use default prompt-based model name.

Notes:
- For production, replace SQLite with a managed DB, add authentication, rate limits, and secure secret storage.
- To deploy on Streamlit Cloud, push this file + requirements to GitHub and configure the secrets there.

"""

import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from PIL import Image
import io
import base64
import traceback

# Optional Gemini import: we try to import the Google Gen AI SDK. If it's not available or not configured,
# the app continues without model functionality.
USE_GEMINI = False
GEMINI_AVAILABLE = False
GEMINI_ERROR = None
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")

try:
    # google-genai installs as `google` package with submodule `genai` in some releases,
    # or as `google_genai`. We'll try the commonly used import first.
    try:
        from google import genai
        GEMINI_AVAILABLE = True
    except Exception:
        # fallback name
        import google_genai as genai  # type: ignore
        GEMINI_AVAILABLE = True

    # Configure client if API key present (some setups use ADC via GOOGLE_APPLICATION_CREDENTIALS)
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        # many setups expose a configure function — adapt if your environment differs
        try:
            genai.configure(api_key=api_key)
            USE_GEMINI = True
        except Exception:
            # Some SDKs rely on ADC and don't need configure(); we'll still try to use the client.
            USE_GEMINI = True
    else:
        # If no API key provided, but the SDK is present, attempt to use ADC (service account) when calling.
        USE_GEMINI = True
except Exception as e:
    GEMINI_ERROR = str(e)
    GEMINI_AVAILABLE = False
    USE_GEMINI = False

DB_PATH = "dwl.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Database helpers ---

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            household_name TEXT,
            address TEXT,
            reported_waste_type TEXT,
            model_waste_type TEXT,
            weight_kg REAL,
            notes TEXT,
            photo_path TEXT,
            status TEXT,
            assigned_collector TEXT
        )
        """
    )
    conn.commit()
    return conn

conn = init_db()

def add_request(household_name, address, reported_waste_type, model_waste_type, weight_kg, notes, photo_path):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO requests (created_at, household_name, address, reported_waste_type, model_waste_type, weight_kg, notes, photo_path, status, assigned_collector) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), household_name, address, reported_waste_type, model_waste_type, weight_kg, notes, photo_path, "OPEN", None),
    )
    conn.commit()

def list_requests(status=None):
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM requests WHERE status=? ORDER BY created_at DESC", (status,))
    else:
        cur.execute("SELECT * FROM requests ORDER BY created_at DESC")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

def assign_collector(request_id, collector_name):
    cur = conn.cursor()
    cur.execute("UPDATE requests SET status=?, assigned_collector=? WHERE id=?", ("ASSIGNED", collector_name, request_id))
    conn.commit()

# --- Simple local image-based fallback classifier (very small heuristic) ---
# This is used if Gemini is not configured; it's intentionally simple and not for production.

def heuristic_image_classify(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        # simple heuristic: if aspect ratio tall -> likely textile; if bright + many colors -> plastic; else paper
        ratio = max(w / h, h / w)
        pixels = img.resize((50, 50)).getdata()
        avg = tuple(sum(p[i] for p in pixels) / len(pixels) for i in range(3))
        brightness = sum(avg) / 3
        if brightness > 130:
            return "Plastic (likely)"
        if ratio > 1.8:
            return "Textile (likely)"
        return "Paper / Cardboard (likely)"
    except Exception:
        return "Unknown"

# --- Gemini wrapper ---

def classify_with_gemini(image_path=None, image_bytes=None):
    """Return a short classification string or None if unavailable."""
    if not USE_GEMINI:
        return None
    try:
        # dynamic import earlier assigned genai (if available)
        from google import genai  # type: ignore

        model = GEMINI_MODEL or os.environ.get("GEMINI_MODEL", "gemini-1.5")
        # Read image bytes
        if image_bytes is None and image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
        if image_bytes is None:
            return None

        # Encode image to base64 (many Gemini examples accept bytes directly; adjust to your SDK version)
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Build a prompt asking the model to classify into a short label and contamination flag
        prompt = (
            "You are an assistant that classifies household waste images into a short label (one of: 'Plastik PET', 'HDPE', 'Kertas', 'Kaca', 'Logam', 'Tekstil', 'Minyak Jelantah', 'Organik', 'Tidak Dapat Didaur Ulang'). "
            "Also estimate contamination level as 'Clean', 'Slightly contaminated', or 'Contaminated'. "
            "Return a single-line comma-separated answer like: LABEL, CONTAMINATION."

"
            "Image (base64):
" + b64
        )

        # The exact API call depends on your genai SDK version. We attempt a common pattern.
        response = genai.generate(
            model=model,
            prompt=prompt,
            max_output_tokens=150,
        )

        # response may be a complex object; attempt to extract text
        text = None
        if hasattr(response, 'text'):
            text = response.text
        elif isinstance(response, dict):
            # some SDKs return dict-like objects
            text = response.get('output', {}).get('text') or response.get('candidates', [{}])[0].get('content')
        else:
            try:
                text = str(response)
            except Exception:
                text = None

        if not text:
            return None

        # Take first line
        first = text.strip().splitlines()[0]
        return first
    except Exception as e:
        # If anything goes wrong, return None so UI can fall back to heuristic
        st.write("(Gemini classification failed — using fallback)")
        st.write(traceback.format_exc())
        return None

# --- Sample collectors (in real app, this would be a DB table) ---
SAMPLE_COLLECTORS = [
    {"name": "Pengepul A", "radius_km": 3, "waste_types": ["Plastik PET", "Kertas", "Logam"]},
    {"name": "Pengrajin Plastik B", "radius_km": 7, "waste_types": ["Plastik PET"]},
    {"name": "Bank Sampah C", "radius_km": 2, "waste_types": ["Kertas", "Kaca", "Logam"]},
]

# --- Streamlit UI ---
st.set_page_config(page_title="Direct Waste Link - Prototype", layout="wide")
st.title("Direct Waste Link (DWL) — Prototype with Gemini (optional)")

if GEMINI_AVAILABLE:
    st.sidebar.markdown("**Gemini SDK:** detected. Model will be used if credentials set.")
else:
    st.sidebar.markdown("**Gemini SDK:** not available — app will use a lightweight heuristic instead.")

role = st.sidebar.selectbox("Saya sebagai", ["Household (Rumah Tangga)", "Collector (Pengepul / Pengrajin)", "Admin"])

if role == "Household (Rumah Tangga)":
    st.header("Buat Permintaan Jemput Sampah")
    with st.form("pickup_form"):
        household_name = st.text_input("Nama Rumah Tangga / Kontak", value="")
        address = st.text_area("Alamat (lengkap)")
        reported_waste_type = st.selectbox("Jenis Sampah (laporkan)", ["Plastik PET", "HDPE", "Kertas", "Kaca", "Logam", "Tekstil", "Minyak Jelantah", "Organik"])
        weight_kg = st.number_input("Perkiraan berat (kg)", min_value=0.0, step=0.1)
        notes = st.text_area("Catatan (opsional)")
        photo = st.file_uploader("Foto sampah (opsional, bantu klasifikasi)", type=["png", "jpg", "jpeg"]) 
        submitted = st.form_submit_button("Minta Jemput")

        if submitted:
            photo_path = None
            model_waste_type = None
            if photo is not None:
                filename = f"{int(datetime.utcnow().timestamp())}_{photo.name}"
                path = os.path.join(UPLOAD_DIR, filename)
                with open(path, "wb") as f:
                    f.write(photo.getbuffer())
                photo_path = path

                # Try Gemini first
                try:
                    with open(path, "rb") as f:
                        image_bytes = f.read()
                    model_waste_type = classify_with_gemini(image_path=path, image_bytes=image_bytes)
                    if not model_waste_type:
                        model_waste_type = heuristic_image_classify(image_bytes)
                except Exception:
                    model_waste_type = heuristic_image_classify(photo.getvalue())

            add_request(household_name, address, reported_waste_type, model_waste_type, float(weight_kg), notes, photo_path)
            st.success("Permintaan jemput berhasil dibuat. Pengepul akan melihat dan menawar.")

    st.subheader("Riwayat Permintaan Saya")
    df = list_requests()
    if not df.empty:
        st.dataframe(df[['id','created_at','reported_waste_type','model_waste_type','weight_kg','status','assigned_collector','photo_path']])
    else:
        st.info("Belum ada permintaan.")

elif role == "Collector (Pengepul / Pengrajin)":
    st.header("Daftar Permintaan Jemput (OPEN)")
    st.write("Sebagai pengepul, pilih permintaan yang sesuai dengan jenis sampah dan radius operasionalmu.")
    df_open = list_requests(status="OPEN")
    if df_open.empty:
        st.info("Tidak ada permintaan OPEN saat ini.")
    else:
        for _, row in df_open.iterrows():
            with st.expander(f"Request #{row['id']} — {row['reported_waste_type']} — {row['model_waste_type']} — {row['weight_kg']} kg"):
                st.write(f"**Nama:** {row['household_name']}")
                st.write(f"**Alamat:** {row['address']}")
                st.write(f"**Laporan Rumah Tangga:** {row['reported_waste_type']}")
                st.write(f"**Prediksi Model:** {row['model_waste_type']}")
                st.write(f"**Catatan:** {row['notes']}")
                if row['photo_path']:
                    try:
                        img = Image.open(row['photo_path'])
                        st.image(img, caption="Foto sampah", use_column_width=True)
                    except Exception:
                        st.write("(Gagal memuat foto)")
                cols = st.columns([1,1,1])
                with cols[0]:
                    if st.button(f"Tampilkan di Peta (mock) - {row['id']}"):
                        st.info("Fitur peta mock — tambahkan integrasi peta di versi berikutnya.")
                with cols[1]:
                    collector_name = st.text_input(f"Namamu untuk assign - {row['id']}", value="Pengepul X", key=f"name_{row['id']}")
                with cols[2]:
                    if st.button(f"Ambil/Assign Request #{row['id']}", key=f"assign_{row['id']}"):
                        assign_collector(int(row['id']), collector_name)
                        st.success(f"Request #{row['id']} berhasil di-assign ke {collector_name}.")
                        st.experimental_rerun()

    st.subheader("Profil Collector (Contoh)")
    st.write("Beberapa contoh collector yang bisa disesuaikan di pengaturan aplikasi atau database:")
    st.table(pd.DataFrame(SAMPLE_COLLECTORS))

elif role == "Admin":
    st.header("Admin Dashboard")
    st.subheader("Semua Permintaan")
    df_all = list_requests()
    if df_all.empty:
        st.info("Belum ada data.")
    else:
        st.dataframe(df_all)

    st.subheader("Stats")
    try:
        total = len(df_all)
        open_count = len(df_all[df_all['status'] == 'OPEN'])
        assigned = len(df_all[df_all['status'] == 'ASSIGNED'])
        st.metric("Total Requests", total)
        st.metric("Open", open_count)
        st.metric("Assigned", assigned)
    except Exception:
        pass

# --- Footer ---
st.markdown("---")
st.write("Prototype DWL — Gemini integration is optional. For production add auth, ACL, peta, notifikasi SMS/WhatsApp, dan sistem pembayaran/token")

# End of file
