import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
import re

# ---------------------------------------------------------
# 1. 페이지 및 테마 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="아프리카 & 글로벌 매출 대시보드",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        border: 1px solid #f1f3f5;
        margin-bottom: 12px;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #868e96;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #212529;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #495057;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 분류 로직 함수
# ---------------------------------------------------------
def classify_product_type(row):
    l1 = str(row.get('Level 1', '')).strip()
    l2 = str(row.get('Level 2', '')).strip()
    
    if l1 == '완제품' and l2 == '기기':
        return '기기'
    elif l1 == '완제품' and l2 in ['시약', '시약류', '카트리지']:
        return '시약'
    elif '시약' in l2 or 'REAGENT' in str(row.get('품명', '')).upper():
        return '시약'
    elif l1 == '완제품':
        return '기타 완제품'
    else:
        return '기타 (상품/부품)'

def classify_device_line(item_name):
    name = str(item_name).upper()
    if 'CHEMICHROMA' in name:
        return 'Chemichroma 라인'
    elif 'AFIAS' in name:
        return 'AFIAS 라인'
    elif 'ICHROMA' in name:
        return 'ichroma 라인'
    elif 'HEMOCHROMA' in name:
        return 'hemochroma 라인'
    elif 'VET' in name:
        return 'Vet (동물용) 라인'
    elif 'CHAMBER' in name or 'I-CHAMBER' in name:
        return 'i-Chamber'
    elif 'THERMO' in name:
        return 'Thermo-block'
    else:
        return '기타 라인업'

def classify_paid_free(row):
    won_amt = pd.to_numeric(row.get('원화금액', 0), errors='coerce') or 0
    fore_price = pd.to_numeric(row.get('외화단가', 0), errors='coerce') or 0
    ship_type = str(row.get('출고구분', '')).upper()
    note = str(row.get('비고(내역)', '')).upper()
    
    if (won_amt == 0 and fore_price == 0) or any(k in ship_type or k in note for k in ['무상', 'FOC', 'SAMPLE', 'DEMO', '데모']):
        return '무상 (FOC/임대)'
    return '유상 판매'

def classify_ghana_partner(cust_name):
    name = str(cust_name).upper()
    if 'DIAGNOMEDICS' in name or 'DIAGNO' in name:
        return 'DiagnoMedics'
    elif 'ALOS' in name:
        return 'Alos'
    else:
        return '기타 가나 고객사'

# ---------------------------------------------------------
# 3. 데이터 로드 (전체 품목 로드)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_all_data(uploaded_files=None):
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
            
            df['Level 1'] = df['Level 1'].astype(str).str.strip()
            df['Level 2'] = df['Level 2'].astype(str).str.strip()
            df['수출국가'] = df['수출국가'].astype(str).str.strip().str.title()
            df['고객'] = df['고객'].astype(str).str.strip()
            df['수량환산'] = pd.to_numeric(df['수량환산'], errors='coerce').fillna(0)
            df['원화금액'] = pd.to_numeric(df['원화금액'], errors='coerce').fillna(0)
            
            if '연도' in df.columns:
                df['연도'] = pd.to_numeric(df['연도'], errors='coerce')
            elif '매출인식年' in df.columns:
                df['연도'] = pd.to_numeric(df['매출인식年'], errors='coerce')
            else:
                year_match = re.search(r'20\d{2}', file_name)
                df['연도'] = int(year_match.group()) if year_match else 2026
                
            # 분류 칼럼 추가
            df['품목 유형'] = df.apply(classify_product_type, axis=1)
            df['제품 라인'] = df['품명'].apply(classify_device_line)
            df['유무상 구분'] = df.apply(classify_paid_free, axis=1)
            df['가나_대리점'] = df['고객'].apply(classify_ghana_partner)
            
            combined_dfs.append(df)
        except Exception:
            continue
        
    return pd.concat(combined_dfs, ignore_index=True) if combined_dfs else None

# ---------------------------------------------------------
# 4. 메인 화면 헤더
# ---------------------------------------------------------
st.markdown("<h2 style='font-weight: 700; color: #111827; margin-bottom: 0px;'>AFRICA & GLOBAL BUSINESS ANALYTICS</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #6b7280; font-size: 0.95rem; margin-bottom: 24px;'>아프리카 지도 중심 기기/시약 대리점 현황 분석 플랫폼</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 사이드바 제어판
# ---------------------------------------------------------
st.sidebar.markdown("### ⚙️ 분석 필터 설정")
uploaded_files = st.sidebar.file_uploader("추가 DB 업로드 (선택)", type=["xlsx"], accept_multiple_files=True)

df_all = load_all_data(uploaded_files)

if df_all is not None and len(df_all) > 0:
    st.sidebar.markdown("---")
    
    # 1. 기기 vs 시약 선택 필터
    type_options = ['통합 (전체)', '기기 전용', '시약 전용']
    selected_type_mode = st.sidebar.radio("📦 품목 유형 선택", options=type_options, index=0)
    
    filtered_df = df_all.copy()
    if selected_type_mode == '기기 전용':
        filtered_df = filtered_df[filtered_df['품목 유형'] == '기기']
    elif selected_type_mode == '시약 전용':
        filtered_df = filtered_df[filtered_df['품목 유형'] == '시약']
        
    # 2. 국가 필터
    all_countries = sorted([c for c in filtered_df['수출국가'].unique() if c and c != 'Nan'])
    selected_countries = st.sidebar.multiselect("🌍 대상 국가 선택", options=all_countries, default=[])
    
    if selected_countries:
        filtered_df = filtered_df[filtered_df['수출국가'].isin(selected_countries)]
        
    # 3. 가나(Ghana) 전용 필터
    is_ghana_included = ('Ghana' in selected_countries) or (len(selected_countries) == 0 and 'Ghana' in all_countries)
    
    if is_ghana_included:
        st.sidebar.markdown("---")
        st.sidebar.markdown("🇬🇭 **가나(Ghana) 대리점 세부 필터**")
        ghana_partners = ['전체 (All)', 'DiagnoMedics', 'Alos', '기타 가나 고객사']
        selected_ghana = st.sidebar.radio("가나 대리점 구분", options=ghana_partners, index=0)
        
        if selected_ghana != '전체 (All)':
            filtered_df = filtered_df[(filtered_df['수출국가'] != 'Ghana') | (filtered_df['가나_대리점'] == selected_ghana)]

    # 4. 연도 및 유/무상 필터
    st.sidebar.markdown("---")
    all_years = sorted([int(y) for y in filtered_df['연도'].dropna().unique()])
    selected_years = st.sidebar.multiselect("📅 조회 연도 선택", options=all_years, default=all_years)
    if selected_years:
        filtered_df = filtered_df[filtered_df['연도'].isin(selected_years)]

    # ---------------------------------------------------------
    # 6. 상단 요약 KPI 카드
    # ---------------------------------------------------------
    total_qty = int(filtered_df['수량환산'].sum())
    total_amt_krw = filtered_df['원화금액'].sum() / 100000000  # 억원 단위
    paid_cnt = int(filtered_df[filtered_df['유무상 구분'] == '유상 판매']['수량환산'].sum())
    free_cnt = int(filtered_df[filtered_df['유무상 구분'] == '무상 (FOC/임대)']['수량환산'].sum())
    cust_cnt = filtered_df['고객'].nunique()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">총 출고 수량</div><div class="metric-value">{total_qty:,} <span style="font-size:1rem;">EA</span></div><div class="metric-sub">{selected_type_mode}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">총 원화 금액</div><div class="metric-value" style="color:#059669;">{total_amt_krw:,.1f} <span style="font-size:1rem;">억원</span></div><div class="metric-sub">매출 인식 기준</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">유상 수량</div><div class="metric-value" style="color:#2563eb;">{paid_cnt:,} <span style="font-size:1rem;">EA</span></div><div class="metric-sub">유상 판매 물량</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">무상 / 샘플</div><div class="metric-value" style="color:#dc2626;">{free_cnt:,} <span style="font-size:1rem;">EA</span></div><div class="metric-sub">FOC / Demo / Sample</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">거래 대리점 수</div><div class="metric-value">{cust_cnt:,} <span style="font-size:1rem;">개사</span></div><div class="metric-sub">고객사 수</div></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 7. 메인 차트 및 탭 (지도 포함)
    # ---------------------------------------------------------
    t1, t2, t3 = st.tabs(["🗺️ 아프리카 지도 & 대리점 분석", "📊 품목/라인업별 현황", "🔍 상세 원본 데이터"])

    # TAB 1: 아프리카 지도 및 국가/대리점 현황
    with t1:
        col_map, col_info = st.columns([6, 4])
        
        with col_map:
            st.markdown("##### 🌍 아프리카 대륙 국가별 출고 현황 지도")
            map_data = filtered_df.groupby('수출국가').agg({'수량환산': 'sum', '원화금액': 'sum'}).reset_index()
            map_data['원화금액_백만'] = map_data['원화금액'] / 1000000
            
            # 아프리카 영역에 집중된 Choropleth Map 생성
            fig_map = px.choropleth(
                map_data,
                locationmode='country names',
                locations='수출국가',
                color='수량환산',
                hover_name='수출국가',
                hover_data={'수량환산': ':,f', '원화금액_백만': ':.1f'},
                color_continuous_scale='Purples',  # 참고 이미지와 유사한 보라 계열
                scope='africa',  # ★ 아프리카 중심으로 확대 설정 ★
                title=""
            )
            fig_map.update_geos(
                showcountries=True, countrycolor="#ced4da",
                showcoastlines=True, coastlinecolor="#adb5bd",
                showland=True, landcolor="#f8f9fa",
                fitbounds="locations"
            )
            fig_map.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=420,
                coloraxis_colorbar=dict(title="수량(EA)")
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with col_info:
            st.markdown("##### 🏢 주요 대리점/고객사 Top 10")
            cust_summary = filtered_df.groupby(['수출국가', '고객'])['수량환산'].sum().reset_index().sort_values(by='수량환산', ascending=False).head(10)
            fig_cust = px.bar(
                cust_summary, x='수량환산', y='고객', color='수출국가',
                orientation='h', text_auto=',.0f',
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_cust.update_layout(
                yaxis={'categoryorder':'total ascending'}, plot_bgcolor='white',
                paper_bgcolor='white', margin=dict(l=10, r=10, t=20, b=10), height=420
            )
            st.plotly_chart(fig_cust, use_container_width=True)

        # 가나 비중 차트 & 피벗 테이블
        st.markdown("---")
        st.markdown("##### 📋 국가 및 고객사별 상세 피벗 분석")
        cust_pivot = filtered_df.pivot_table(
            index=['수출국가', '고객'], 
            columns='품목 유형', 
            values='수량환산', 
            aggfunc='sum', 
            fill_value=0,
            margins=True,
            margins_name="총계"
        )
        st.dataframe(cust_pivot.style.format("{:,.0f}"), use_container_width=True, height=350)

    # TAB 2: 품목/라인업별 현황
    with t2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🧪 제품 라인업별 출고 점유율")
            line_summary = filtered_df.groupby('제품 라인')['수량환산'].sum().reset_index()
            fig_line = px.bar(line_summary, x='제품 라인', y='수량환산', color='제품 라인', text_auto=',.0f')
            fig_line.update_layout(plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=10, r=10, t=20, b=10), height=380, showlegend=False)
            st.plotly_chart(fig_line, use_container_width=True)

        with col2:
            st.markdown("##### 📈 연도별 출고 추이 (기기/시약/기타)")
            yearly_line = filtered_df.groupby(['연도', '품목 유형'])['수량환산'].sum().reset_index()
            fig_yearly = px.line(yearly_line, x='연도', y='수량환산', color='품목 유형', markers=True)
            fig_yearly.update_layout(plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=10, r=10, t=20, b=10), height=380)
            st.plotly_chart(fig_yearly, use_container_width=True)

    # TAB 3: 원본 상세
    with t3:
        st.markdown("##### 🔎 선택한 필터 기준 상세 원본 내역")
        st.dataframe(
            filtered_df[['연도', '수출국가', '고객', '가나_대리점', '품목 유형', '품명', '제품 라인', '유무상 구분', '수량환산', '원화금액']]
            .sort_values(by=['수출국가', '고객', '연도']),
            use_container_width=True, height=500
        )

else:
    st.info("💡 `data/` 폴더 내에 엑셀 데이터 파일들이 업로드되어 있는지 확인해주세요.")
