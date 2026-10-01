import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
import re

# ---------------------------------------------------------
# 1. 페이지 대시보드 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="국가별 기기 누적 및 월별 출고 현황",
    page_icon="📊",
    layout="wide"
)

# 깔끔한 CSS 스타일링
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #e9ecef;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #6c757d;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #212529;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 기기 라인업 및 유/무상 분류 함수
# ---------------------------------------------------------
def classify_device_line(item_name):
    name = str(item_name).upper()
    if 'AFIAS' in name:
        return 'AFIAS 라인'
    elif 'ICHROMA' in name and 'CHEMICHROMA' not in name:
        return 'ichroma 라인'
    elif 'CHEMICHROMA' in name:
        return 'Chemichroma 라인'
    elif 'HEMOCHROMA' in name:
        return 'hemochroma 라인'
    elif 'VET' in name:
        return 'Vet (동물용) 라인'
    elif 'CHAMBER' in name or 'I-CHAMBER' in name:
        return 'i-Chamber'
    elif 'THERMO' in name:
        return 'Thermo-block'
    else:
        return '기타 기기'

def classify_paid_free(row):
    won_amt = pd.to_numeric(row.get('원화금액', 0), errors='coerce') or 0
    fore_price = pd.to_numeric(row.get('외화단가', 0), errors='coerce') or 0
    ship_type = str(row.get('출고구분', '')).upper()
    note = str(row.get('비고(내역)', '')).upper()
    
    if (won_amt == 0 and fore_price == 0) or any(k in ship_type or k in note for k in ['무상', 'FOC', 'SAMPLE', 'DEMO', '데모']):
        return '무상 (FOC/임대/샘플)'
    return '유상 판매'

# ---------------------------------------------------------
# 3. 데이터 로드 및 전처리 (기기 전용)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data(uploaded_files=None):
    combined_dfs = []
    local_files = glob.glob("data/*.xlsx") + glob.glob("*.xlsx")
    target_files = uploaded_files if (uploaded_files and len(uploaded_files) > 0) else local_files
    
    if not target_files:
        return None
        
    for file in target_files:
        file_name = file.name if hasattr(file, 'name') else os.path.basename(file)
        try:
            xls = pd.ExcelFile(file)
            df_raw = pd.read_excel(file, sheet_name=xls.sheet_names[0])
            
            df = df_raw.iloc[4:].copy()
            df.columns = df_raw.iloc[3].values
            
            # 기본 데이터 정형화
            df['Level 1'] = df['Level 1'].astype(str).str.strip()
            df['Level 2'] = df['Level 2'].astype(str).str.strip()
            df['수출국가'] = df['수출국가'].astype(str).str.strip().str.title()
            df['수량환산'] = pd.to_numeric(df['수량환산'], errors='coerce').fillna(0)
            
            # 연도 및 월 추출
            if '연도' in df.columns:
                df['연도'] = pd.to_numeric(df['연도'], errors='coerce')
            else:
                year_match = re.search(r'20\d{2}', file_name)
                df['연도'] = int(year_match.group()) if year_match else 2026
                
            if '월' in df.columns:
                df['월'] = pd.to_numeric(df['월'], errors='coerce').fillna(1).astype(int)
            else:
                df['월'] = 1
                
            # 순수 '기기' 완제품만 추출
            devices = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
            devices['기기 라인업'] = devices['품명'].apply(classify_device_line)
            devices['유무상 구분'] = devices.apply(classify_paid_free, axis=1)
            
            # 연월 칼럼 생성 (예: 2024-03)
            devices['연월'] = devices.apply(lambda r: f"{int(r['연도'])}년 {int(r['월']):02d}월", axis=1)
            
            combined_dfs.append(devices)
        except Exception:
            continue
        
    return pd.concat(combined_dfs, ignore_index=True) if combined_dfs else None

# ---------------------------------------------------------
# 4. 헤더
# ---------------------------------------------------------
st.title("📊 국가별 기기 누적 및 월별 출고 현황")
st.caption("회사/고객사 정보 없이 국가 단위로 기기 누적 수량 및 유/무상 출고 현황을 분석합니다.")

# ---------------------------------------------------------
# 5. 사이드바 제어판 (국가 중심)
# ---------------------------------------------------------
st.sidebar.header("⚙️ 검색 필터")
uploaded_files = st.sidebar.file_uploader("엑셀 파일 업로드", type=["xlsx"], accept_multiple_files=True)

df = load_data(uploaded_files)

if df is not None and len(df) > 0:
    # 1. 국가 선택 (기본값: 전체)
    all_countries = sorted([c for c in df['수출국가'].unique() if c and c != 'Nan'])
    selected_country = st.sidebar.selectbox("🌍 국가 선택", options=["전체 국가"] + all_countries, index=0)
    
    # 2. 연도 선택
    all_years = sorted([int(y) for y in df['연도'].dropna().unique()])
    selected_years = st.sidebar.multiselect("📅 연도 선택", options=all_years, default=all_years)
    
    # 3. 유/무상 선택
    paid_options = sorted(df['유무상 구분'].unique())
    selected_paid = st.sidebar.multiselect("💳 유/무상 구분", options=paid_options, default=paid_options)
    
    # 필터 적용
    filtered = df.copy()
    if selected_country != "전체 국가":
        filtered = filtered[filtered['수출국가'] == selected_country]
    if selected_years:
        filtered = filtered[filtered['연도'].isin(selected_years)]
    if selected_paid:
        filtered = filtered[filtered['유무상 구분'].isin(selected_paid)]

    # ---------------------------------------------------------
    # 6. 상단 요약 KPI 카드
    # ---------------------------------------------------------
    total_qty = int(filtered['수량환산'].sum())
    paid_qty = int(filtered[filtered['유무상 구분'] == '유상 판매']['수량환산'].sum())
    free_qty = int(filtered[filtered['유무상 구분'] != '유상 판매']['수량환산'].sum())
    
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">총 기기 누적 수량</div><div class="metric-value">{total_qty:,} 대</div></div>""", unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">유상 판매 누적</div><div class="metric-value" style="color:#2563eb;">{paid_qty:,} 대</div></div>""", unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">무상(FOC/데모) 누적</div><div class="metric-value" style="color:#dc2626;">{free_qty:,} 대</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 7. 메인 시각화 (월별 출고 + 기기 누적)
    # ---------------------------------------------------------
    t1, t2 = st.tabs(["📅 월별 기기 출고 추이", "🏛️ 국가별/기기별 누적 현황"])

    # TAB 1: 월별 출고 현황
    with t1:
        st.subheader("📅 월별 어떤 기기가 얼만큼 나갔는지 확인")
        
        # 월별 + 기기 라인업 집계
        monthly_df = filtered.groupby(['연도', '월', '기기 라인업', '유무상 구분'])['수량환산'].sum().reset_index()
        monthly_df['연월'] = monthly_df.apply(lambda r: f"{int(r['연도'])}년 {int(r['월']):02d}월", axis=1)
        monthly_df = monthly_df.sort_values(by=['연도', '월'])
        
        # 그래프
        fig_month = px.bar(
            monthly_df, 
            x='연월', 
            y='수량환산', 
            color='기기 라인업', 
            pattern_shape='유무상 구분', # 유무상을 패턴으로 구분
            text_auto=',.0f',
            title=f"[{selected_country}] 월별 기기 출고 수량 (유/무상 구분)",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_month.update_layout(plot_bgcolor='white', paper_bgcolor='white', height=420)
        st.plotly_chart(fig_month, use_container_width=True)
        
        # 월별 표
        st.markdown("##### 📋 월별 상세 출고 표")
        month_pivot = filtered.pivot_table(
            index=['연도', '월'],
            columns=['기기 라인업', '유무상 구분'],
            values='수량환산',
            aggfunc='sum',
            fill_value=0
        )
        st.dataframe(month_pivot.style.format("{:,.0f}"), use_container_width=True)

    # TAB 2: 국가별/기기별 누적 현황
    with t2:
        st.subheader("🏛️ 국가별 기기 누적 수량")
        
        col_c1, col_c2 = st.columns([6, 4])
        
        with col_c1:
            country_summary = filtered.groupby(['수출국가', '기기 라인업'])['수량환산'].sum().reset_index()
            fig_country = px.bar(
                country_summary, 
                x='수량환산', 
                y='수출국가', 
                color='기기 라인업', 
                orientation='h',
                text_auto=',.0f',
                title="국가별 누적 기기 수량"
            )
            fig_country.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor='white', height=450)
            st.plotly_chart(fig_country, use_container_width=True)
            
        with col_c2:
            st.markdown("##### 💡 유/무상 누적 비율")
            paid_summary = filtered.groupby('유무상 구분')['수량환산'].sum().reset_index()
            fig_pie = px.pie(paid_summary, values='수량환산', names='유무상 구분', hole=0.4, color_discrete_sequence=['#2563eb', '#dc2626'])
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(height=450)
            st.plotly_chart(fig_pie, use_container_width=True)

        # 국가 - 기기 라인업 피벗 테이블
        st.markdown("##### 📋 국가별 기기 라인업 피벗 요약 (회사 구분 없음)")
        country_pivot = filtered.pivot_table(
            index='수출국가',
            columns='기기 라인업',
            values='수량환산',
            aggfunc='sum',
            fill_value=0,
            margins=True,
            margins_name="총 누적"
        )
        st.dataframe(country_pivot.style.format("{:,.0f}"), use_container_width=True)

else:
    st.info("💡 `data/` 폴더에 데이터 파일이 올라와 있는지 확인해 주세요.")
