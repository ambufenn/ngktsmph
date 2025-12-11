"""
Streamlit app: Direct Waste Link (DWL) - Prototype with Gemini (optional)
File: streamlit_direct_waste_app.py

Summary:
- Single-file Streamlit prototype for households to create pickup requests and for collectors to accept them.
- Optional integration with Google Gemini (via Google Gen AI Python SDK) to auto-classify uploaded waste photos.
- SQLite backend for local testing; easy to push to GitHub and deploy to Streamlit Cloud.
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

# Optional Gemini integration
USE_GEMINI = False
GEMINI_AVAILABLE = False
GEMINI_ERROR = None
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "")

try:
    try:
        from google import genai
        GEMINI_AVAILABLE = True
    except Exception:
        import google_genai as genai  # fallback
        GEMINI_AVAILABLE = True

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            USE_GEMINI = True
        except:
            USE_GEMINI = True
    else:
        USE_GEMINI = True
except Exception as e:
    GEMINI_ERROR = str(e)
    GEMINI_AVAILABLE = False
    USE_GEMINI = False

DB_PATH = "dwl.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- DB ----------------

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

# ---------------- Fallback heuristic classifier ----------------

def heuristic_image_classify(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        ratio = max(w / h, h / w)
        pixels = img.resize((50, 50)).getdata()
        avg = tuple(sum(p[i] for p in pixels) / len(pixels) for i in range(3))
        brightness = sum(avg) / 3
        if brightness > 130:
            return "Plastic (likely)"
        if ratio > 1.8:
            return "Textile (likely)"
        return "Paper / Cardboard (likely)"
    except:
        return "Unknown"

# ---------------- Gemini wrapper ----------------

def classify_with_gemini(image_path=None, image_bytes=None):
    if not USE_GEMINI:
        return None
    try:
        from google import genai  # type: ignore
        model = GEMINI_MODEL or "gemini-1.5"

        if image_bytes is None and image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

        if image_bytes is None:
            return None

        b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "You are an assistant that classifies household waste images into a short label "
            "(one of: 'Plastik PET', 'HDPE', 'Kertas', 'Kaca', 'Logam', 'Tekstil', "
            "'Minyak Jelantah', 'Organik', 'Tidak Dapat Didaur Ulang'). "
            "Also estimate contamination level as 'Clean', 'Slightly contaminated', or 'Contaminated'. "
            "Return a single-line comma-separated answer like: LABEL, CONTAMINATION.\n\n"
            "Image (base64):\n" + b64
        )

        response = genai.generate(
            model=model,
            prompt=prompt,
            max_output_tokens=150,
        )

        text = None
        if hasattr(response, "text"):
            text = response.text
        elif isinstance(response, dict):
            text = response.get("output", {}).get("text") or response.get("candidates", [{}])[0].get("content")
        else:
            text = str(response)

        if not text:
            return None

        return text.strip().splitlines()[0]

    except Exception:
        st.write("(Gemini classification failed — using fallback)")
        st.write(traceback.format_exc())
        return None

# ---------------- Sample collectors ----------------

SAMPLE_COLLECTORS = [
    {"name": "Pengepul A", "radius_km": 3, "waste_types": ["Plastik PET", "Kertas", "Logam"]},
    {"name": "Pengrajin Plastik B", "radius_km": 7, "waste_types": ["Plastik PET"]},
    {"name": "Bank Sampah C", "radius_km": 2, "waste_types": ["Kertas", "Kaca", "Logam"]},
]

# ---------------- Streamlit UI ----------------

st.set_page_config(page_title="Direct Waste Link - Prototype", layout="wide")
st.title("Direct Waste Link (DWL) — Prototype with Gemini (optional)")

if GEMINI_AVAILABLE:
    st.sidebar.markdown("**Gemini SDK:** detected. Model will be used if credentials set.")
else:
    st.sidebar.markdown("**Gemini SDK:** not available — using heuristic classifier.")

role = st.sidebar.selectbox("Saya sebagai", ["Household (Rumah Tangga)", "Collector (Pengepul / Pengrajin)", "Admin"])

# ---------------- Household ----------------

if role == "Household (Rumah Tangga)":
    st.header("Buat Permintaan Jemput Sampah")
    with st.form("pickup_form"):
        household_name = st.text_input("Nama Rumah Tangga / Kontak", value="")
        address = st.text_area("Alamat (lengkap)")
        reported_waste_type = st.selectbox(
            "Jenis Sampah (laporkan)",
            ["Plastik PET", "HDPE", "Kertas", "Kaca", "Logam", "Tekstil", "Minyak Jelantah", "Organik"],
        )
        weight_kg = st.number_input("Perkiraan berat (kg)", min_value=0.0, step=0.1)
        notes = st.text_area("Catatan (opsional)")
        photo = st.file_uploader("Foto sampah (opsional)", type=["png", "jpg", "jpeg"])
        submitted = st.form_submit_button("Minta Jemput")

        if submitted:
            photo_path = None
            model_waste_type = None

            if photo:
                filename = f"{int(datetime.utcnow().timestamp())}_{photo.name}"
                path = os.path.join(UPLOAD_DIR, filename)
                with open(path, "wb") as f:
                    f.write(photo.getbuffer())
                photo_path = path

                try:
                    image_bytes = photo.getvalue()
                    model_waste_type = classify_with_gemini(image_path=path, image_bytes=image_bytes)
                    if not model_waste_type:
                        model_waste_type = heuristic_image_classify(image_bytes)
                except:
                    model_waste_type = heuristic_image_classify(photo.getvalue())

            add_request(
                household_name,
                address,
                reported_waste_type,
                model_waste_type,
                float(weight_kg),
                notes,
                photo_path,
            )
            st.success("Permintaan jemput berhasil dibuat. Pengepul akan melihat dan menawar.")

    st.subheader("Riwayat Permintaan Saya")
    df = list_requests()
    if len(df) > 0:
        st.dataframe(df[["id", "created_at", "reported_waste_type", "model_waste_type", "weight_kg", "status", "assigned_collector"]])
    else:
        st.info("Belum ada permintaan.")

# ---------------- Collector ----------------

elif role == "Collector (Pengepul / Pengrajin)":
    st.header("Daftar Permintaan Jemput (OPEN)")
    df_open = list_requests(status="OPEN")

    if df_open.empty:
        st.info("Tidak ada permintaan OPEN saat ini.")
    else:
        for _, row in df_open.iterrows():
            with st.expander(f"Request #{row['id']} — {row['reported_waste_type']} — {row['model_waste_type']} — {row['weight_kg']} kg"):
                st.write(f"**Nama:** {row['household_name']}")
                st.write(f"**Alamat:** {row['address']}")
                st.write(f"**Laporan:** {row['reported_waste_type']}")
                st.write(f"**Prediksi Model:** {row['model_waste_type']}")
                st.write(f"**Catatan:** {row['notes']}")

                if row["photo_path"]:
                    try:
                        img = Image.open(row["photo_path"])
                        st.image(img, caption="Foto sampah", use_column_width=True)
                    except:
                        st.write("(Gagal memuat foto)")

                cols = st.columns([1,1,1])
                with cols[0]:
                    st.button(f"Tampilkan di Peta (mock) - {row['id']}")

                with cols[1]:
                    collector_name = st.text_input(f"Namamu - {row['id']}", value="Pengepul X", key=f"name_{row['id']}")

                with cols[2]:
                    if st.button(f"Ambil Request #{row['id']}", key=f"assign_{row['id']}"):
                        assign_collector(int(row["id"]), collector_name)
                        st.success(f"Request #{row['id']} berhasil di-assign ke {collector_name}.")
                        st.experimental_rerun()

    st.subheader("Profil Collector (Contoh)")
    st.table(pd.DataFrame(SAMPLE_COLLECTORS))

# ---------------- Admin ----------------

elif role == "Admin":
    st.header("Admin Dashboard")
    df_all = list_requests()

    if df_all.empty:
        st.info("Belum ada data.")
    else:
        st.dataframe(df_all)

        st.subheader("Stats")
        st.metric("Total Requests", len(df_all))
        st.metric("Open", len(df_all[df_all["status"] == "OPEN"]))
        st.metric("Assigned", len(df_all[df_all["status"] == "ASSIGNED"]))

# ---------------- Footer ----------------

st.markdown("---")
st.write("Prototype DWL — Gemini optional. Tambahkan auth, peta, notifikasi, dan sistem penawaran harga untuk produksi.")
