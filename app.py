from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# 0. PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Africa Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"


# =========================================================
# 1. STYLE
# =========================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #F6F8FB; }
    .block-container { max-width: 1550px; padding-top: 1.3rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { background-color: #0E2439; }
    [data-testid="stSidebar"] * { color: #F8FAFC; }
    [data-testid="stSidebar"] input { color: #101828 !important; }

    .dashboard-title {
        font-size: 2.0rem;
        font-weight: 800;
        color: #101828;
        letter-spacing: -0.03em;
        margin-bottom: 0.15rem;
    }
    .dashboard-subtitle {
        color: #667085;
        font-size: 0.95rem;
        margin-bottom: 1.0rem;
    }
    .section-label {
        font-size: 0.82rem;
        font-weight: 800;
        color: #475467;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E4E7EC;
        border-radius: 14px;
        padding: 0.9rem 1rem;
        box-shadow: 0 1px 2px rgba(16,24,40,0.03);
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #E4E7EC;
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}


# =========================================================
# 2. STANDARDIZATION RULES
# =========================================================
COLUMN_ALIASES = {
    "date": ["마감일자/출고일자", "마감일자", "출고일자", "매출일자", "일자", "Date"],
    "customer": ["고객", "거래처", "고객명", "거래처명", "Customer", "Company"],
    "customer_id": ["거래처번호", "고객번호", "Customer No", "Customer ID"],
    "country": ["수출국가", "국가", "Country", "Export Country"],
    "region": ["Region", "지역", "권역", "대륙"],
    "currency": ["환종", "통화", "Currency"],
    "sales_foreign": ["외화금액", "외화매출", "외화 매출", "Foreign Amount"],
    "sales_krw": ["원화금액", "원화매출", "원화 매출", "KRW Amount"],
    "qty": ["수량환산", "수량", "판매수량", "출고수량", "Qty", "Quantity"],
    "month": ["매출인식月", "매출인식월", "월", "Month"],
    "item_code": ["품번", "제품코드", "Item Code", "SKU"],
    "item_name": ["품명", "제품명", "Item Name", "Product"],
    "level1": ["Level 1", "Level1", "LEVEL 1"],
    "level2": ["Level 2", "Level2", "LEVEL 2"],
    "level3": ["Level 3", "Level3", "LEVEL 3"],
    "level4": ["Level 4", "Level4", "LEVEL 4"],
