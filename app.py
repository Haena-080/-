from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# 0. PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Africa Sales Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"

# =========================================================
# 1. DESIGN SYSTEM
# =========================================================
st.markdown(
    """
    <style>
    :root {
        --bg:#F5F7FA;
        --panel:#FFFFFF;
        --ink:#101828;
        --muted:#667085;
        --line:#E4E7EC;
        --navy:#102A43;
        --blue:#2563EB;
        --soft:#EEF4FF;
    }
    .stApp { background: var(--bg); }
    .block-container { max-width: 1540px; padding-top: 1.6rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background:#0D2238; }
    [data-testid="stSidebar"] * { color:#F8FAFC; }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea { color:#101828 !important; }
    .hero-title { font-size:2.05rem; font-weight:780; color:var(--ink); letter-spacing:-0.035em; margin:0; }
    .hero-sub { color:var(--muted); font-size:.92rem; margin:.2rem 0 1.25rem 0; }
    .section-title { color:var(--ink); font-size:1.08rem; font-weight:720; margin:.2rem 0 .65rem 0; }
    .eyebrow { color:#475467; font-size:.76rem; font-weight:700; letter-spacing:.07em; text-transform:uppercase; }
    div[data-testid="stMetric"] {
        background:var(--panel); border:1px solid var(--line); border-radius:15px;
        padding:1rem 1.05rem; box-shadow:0 1px 2px rgba(16,24,40,.025);
    }
    div[data-testid="stMetricLabel"] { color:var(--muted); }
    div[data-testid="stMetricValue"] { color:var(--ink); }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    .scope-pill {
        display:inline-block; padding:.30rem .60rem; border:1px solid #D0D5DD;
        background:#fff; border-radius:999px; color:#344054; font-size:.78rem; margin-right:.35rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}
CHART_LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=20, r=20, t=50, b=20),
    font=dict(family="Arial", color="#344054"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#FFFFFF",
    hoverlabel=dict(bgcolor="white"),
)

# =========================================================
# 2. YEARLY DB COLUMN STANDARDIZATION
# =========================================================
COLUMN_ALIASES = {
    "date": ["마감일자/출고일자", "마감일자", "출고일자", "매출일자", "일자", "Date"],
    "year_raw": ["연도", "매출인식年", "매출인식년", "Year", "YEAR"],
    "month_raw": ["월", "매출인식月", "매출인식월", "Month", "MONTH"],
    "customer_raw": ["고객", "거래처", "고객명", "거래처명", "Customer", "Company"],
    "customer_id": ["거래처번호", "고객번호", "Customer No", "Customer ID"],
    "country_raw": ["수출국가", "국가", "Country", "Export Country"],
    "region": ["Region", "지역", "권역", "대륙"],
    "currency": ["환종", "통화", "Currency"],
    "sales_fx": ["외화금액", "외화매출", "외화 매출", "Foreign Amount", "Sales USD"],
    "sales_krw": ["원화금액", "원화매출", "원화 매출", "KRW Amount", "Sales KRW"],
    "qty": ["수량환산", "수량", "판매수량", "출고수량", "Qty", "Quantity"],
    "item_code": ["품번", "제품코드", "Item Code", "SKU"],
    "item_name": ["품명", "제품명", "Item Name", "Product"],
    "level1": ["Level 1", "Level1", "LEVEL 1"],
