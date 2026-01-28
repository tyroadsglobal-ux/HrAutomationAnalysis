import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine, text
from fpdf import FPDF
from io import BytesIO

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="HR Offer Analytics",
    layout="wide"
)
st.title("📊 HR Offer Analytics")

# ================= DB CONFIG =================
TABLE_NAME = "offer"

engine = create_engine(
    f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
    connect_args={"ssl": {}}
)

# ================= LOAD FILTER DATA =================
@st.cache_data(ttl=600)
def load_positions():
    query = f"""
        SELECT DISTINCT position
        FROM {TABLE_NAME}
        WHERE position IS NOT NULL
    """
    return pd.read_sql(query, engine)

positions_df = load_positions()

# ================= TOP FILTER BAR =================
st.markdown("### 🔍 Filters")
f1, f2, f3 = st.columns(3)

with f1:
    candidate_response = st.selectbox(
        "Candidate Response",
        ["All", "PENDING", "ACCEPTED", "REJECTED"]
    )

with f2:
    position = st.selectbox(
        "Position",
        ["All"] + sorted(positions_df["position"].tolist())
    )

with f3:
    date_range = st.date_input(
        "Created Date Range",
        value=None
    )

st.divider()

# ================= FETCH DATA =================
@st.cache_data(ttl=300)
def fetch_data(candidate_response, position, date_range):
    query = f"""
        SELECT id, email, name, position, salary, status, candidate_response, created_at
        FROM {TABLE_NAME}
        WHERE 1=1
    """
    params = {}

    if candidate_response != "All":
        query += " AND candidate_response = :candidate_response"
        params["candidate_response"] = candidate_response

    if position != "All":
        query += " AND position = :position"
        params["position"] = position

    if isinstance(date_range, tuple) and len(date_range) == 2:
        query += " AND DATE(created_at) BETWEEN :start AND :end"
        params["start"] = date_range[0]
        params["end"] = date_range[1]

    query += " ORDER BY id ASC"

    df = pd.read_sql(text(query), engine, params=params)
    df["candidate_response"] = df["candidate_response"].str.upper()  # normalize values
    return df

df = fetch_data(candidate_response, position, date_range)

# ================= METRICS =================
st.subheader("📌 Key Metrics")
m1, m2, m3, m4 = st.columns(4)

m1.metric("Total Offers", len(df))
m2.metric("Accepted", len(df[df["candidate_response"] == "ACCEPTED"]))
m3.metric("Rejected", len(df[df["candidate_response"] == "REJECTED"]))
m4.metric(
    "Pending",
    len(df[(df["candidate_response"].isna()) | (df["candidate_response"] == "PENDING")])
)

# ================= DATA TABLE =================
st.subheader("📄 Offer Records")
df_display = df.copy()
df_display.insert(0, "S.No", range(1, len(df_display) + 1))  # optional serial number
st.dataframe(df_display, use_container_width=True)

st.divider()

# ================= DOWNLOAD REPORTS =================
st.subheader("⬇️ Download Reports")

# ----- Excel -----
excel_buffer = BytesIO()
df.to_excel(excel_buffer, index=False, engine="openpyxl")
excel_buffer.seek(0)

st.download_button(
    "📥 Download Excel",
    excel_buffer,
    file_name="offer_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ----- PDF -----
def generate_pdf(dataframe):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", size=8)
    
    for _, row in dataframe.iterrows():
        pdf.multi_cell(0, 5, str(row.to_dict()))
        pdf.ln(1)
    
    return pdf.output(dest="S").encode("latin-1")

st.download_button(
    "📄 Download PDF (Top 100)",
    generate_pdf(df.head(100)),
    file_name="offer_report.pdf",
    mime="application/pdf"
)
