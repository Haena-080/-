import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import os
import re

# ---------------------------------------------------------
# 1. 페이지 테마 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="Global Device Business Review",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. 전문 대시보드용 커스텀 CSS (모던 카드/섀도우 UI 스타일)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* 전체 배경색 - 연한 쿨그레이 */
    .stApp {
        background-color: #f8f9fa;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 사이드바 스타일링 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    
    /* 카드 컴포넌트 스타일링 */
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        border: 1px solid #f1f3f5;
        margin-bottom: 12px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #868e96;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #212529;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #495057;
        margin-top: 6px;
    }
    
    /* 탭 디자인 모던화 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        padding: 4px 0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        font-weight: 600;
        color: #495057;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border-color: #1f2937 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. 데이터 로직 및 비즈니스 함수
# ---------------------------------------------------------
def classify_device_line(item_name):
    name = str(item_name).upper()
    if 'AFIAS' in name: return 'AFIAS 라인'
    elif 'ICHROMA' in name: return 'ichroma 라인'
    elif 'HEMOCHROMA' in name: return 'hemochroma 라인'
    elif 'VET' in name: return 'Vet (동물용) 라인'
    elif 'CHAMBER' in name or 'I-CHAMBER' in name: return 'i-Chamber'
    elif 'THERMO' in name: return 'Thermo-block'
    else: return '기타 기기'

def classify_paid_free(row):
    won_amt = pd.to_numeric(row.get('원화금액', 0), errors='coerce') or 0
    fore_price = pd.to_numeric(row.get('외화단가', 0), errors='coerce') or 0
    ship_type = str(row.get('출고구분', '')).upper()
    note = str(row.get('비고(내역)', '')).upper()
    
    if (won_amt == 0 and fore_price == 0) or any(k in ship_type or k in note for k in ['무상', 'FOC', 'SAMPLE', 'DEMO', '데모']):
        return '무상 (FOC/임대)'
    return '유상 판매'

@st.cache_data(ttl=3600)
def load_all_data(uploaded_files=None):
    combined_dfs = []
    local_files = glob.glob("data/*.xlsx") + glob.glob("*.xlsx")
    target_files = uploaded_files if (uploaded_files and len(uploaded_files) > 0) else local_files
    
    if not target_files: return None
        
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
            df['담당자'] = df['담당자'].astype(str).str.strip()
            df['팀 분류'] = df['팀 분류'].astype(str).str.strip()
            df['수량환산'] = pd.to_numeric(df['수량환산'], errors='coerce').fillna(0)
            
            if '연도' in df.columns: df['연도'] = pd.to_numeric(df['연도'], errors='coerce')
            elif '매출인식年' in df.columns: df['연도'] = pd.to_numeric(df['매출인식年'], errors='coerce')
            else:
                year_match = re.search(r'20\d{2}', file_name)
                df['연도'] = int(year_match.group()) if year_match else 2026
                
            devices = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
            devices['기기 라인'] = devices['품명'].apply(classify_device_line)
            devices['유무상 구분'] = devices.apply(classify_paid_free, axis=1)
            combined_dfs.append(devices)
        except Exception:
            continue
        
    return pd.concat(combined_dfs, ignore_index=True) if combined_dfs else None

# ---------------------------------------------------------
# 4. 헤더 레이아웃
# ---------------------------------------------------------
st.markdown("<h2 style='font-weight: 700; color: #111827; margin-bottom: 0px;'>MANAGEMENT BUSINESS REVIEW</h2>", unsafe_allow_html=True)
st.markdown("<p style='color: #6b7280; font-size: 0.95rem; margin-bottom: 24px;'>Global Device Distribution & Executive Sales Performance Analytics</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. 데이터 읽기 및 사이드바 필터
# ---------------------------------------------------------
st.sidebar.markdown("### ⚙️ Control Panel")
uploaded_files = st.sidebar.file_uploader("추가 DB 업로드", type=["xlsx"], accept_multiple_files=True)

devices_df = load_all_data(uploaded_files)

if devices_df is not None and len(devices_df) > 0:
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🔍 Filter Options")
    
    all_years = sorted([int(y) for y in devices_df['연도'].dropna().unique()])
    selected_years = st.sidebar.multiselect("연도 선택", options=all_years, default=all_years)
    if selected_years: devices_df = devices_df[devices_df['연도'].isin(selected_years)]
        
    paid_options = sorted(devices_df['유무상 구분'].unique())
    selected_paid = st.sidebar.multiselect("유/무상 구분", options=paid_options, default=paid_options)
    if selected_paid: devices_df = devices_df[devices_df['유무상 구분'].isin(selected_paid)]
        
    teams = sorted([t for t in devices_df['팀 분류'].unique() if t and t != 'nan'])
    selected_teams = st.sidebar.multiselect("담당 팀", options=teams, default=[])
    if selected_teams: devices_df = devices_df[devices_df['팀 분류'].isin(selected_teams)]

    # ---------------------------------------------------------
    # 6. 상단 Executive Summary KPI Cards (이미지 스타일)
    # ---------------------------------------------------------
    total_qty = int(devices_df['수량환산'].sum())
    paid_cnt = int(devices_df[devices_df['유무상 구분'] == '유상 판매']['수량환산'].sum())
    free_cnt = int(devices_df[devices_df['유무상 구분'] == '무상 (FOC/임대)']['수량환산'].sum())
    country_cnt = devices_df['수출국가'].nunique()
    cust_cnt = devices_df['고객'].nunique()
    paid_ratio = (paid_cnt / total_qty * 100) if total_qty > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">총 기기 출고량</div>
            <div class="metric-value">{total_qty:,} <span style="font-size:1rem;">대</span></div>
            <div class="metric-sub">전체 누적 출고</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">유상 판매 비중</div>
            <div class="metric-value" style="color: #2563eb;">{paid_ratio:.1f}%</div>
            <div class="metric-sub">총 {paid_cnt:,} 대</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">무상/임대 기기</div>
            <div class="metric-value" style="color: #dc2626;">{free_cnt:,} <span style="font-size:1rem;">대</span></div>
            <div class="metric-sub">FOC / Demo / Sample</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">진출 국가 수</div>
            <div class="metric-value">{country_cnt:,} <span style="font-size:1rem;">개국</span></div>
            <div class="metric-sub">글로벌 커버리지</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">활성 거래 고객사</div>
            <div class="metric-value">{cust_cnt:,} <span style="font-size:1rem;">개사</span></div>
            <div class="metric-sub">글로벌 파트너/고객</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 7. 메인 대시보드 차트 영역
    # ---------------------------------------------------------
    t1, t2, t3 = st.tabs(["📊 Performance Overview", "🗺️ Global Distribution", "👥 Partner & Country Detail"])

    with t1:
        col_left, col_right = st.columns([6, 4])
        
        with col_left:
            st.markdown("##### 연도별 출고 추이 및 유/무상 구성비")
            yearly_data = devices_df.groupby(['연도', '유무상 구분'])['수량환산'].sum().reset_index()
            
            # 전문적인 차트 컬러 팔레트 적용
            fig_bar = px.bar(
                yearly_data, x='연도', y='수량환산', color='유무상 구분',
                barmode='stack', text_auto=',.0f',
                color_discrete_map={'유상 판매': '#2563eb', '무상 (FOC/임대)': '#cbd5e1'}
            )
            fig_bar.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                margin=dict(l=10, r=10, t=30, b=10), height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_bar.update_xaxes(showgrid=False)
            fig_bar.update_yaxes(showgrid=True, gridcolor='#f1f3f5')
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.markdown("##### 라인업별 출고 점유율")
            line_df = devices_df.groupby('기기 라인')['수량환산'].sum().reset_index()
            fig_pie = px.pie(
                line_df, values='수량환산', names='기기 라인', hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                margin=dict(l=10, r=10, t=30, b=10), height=380,
                legend=dict(orientation="v", yanchor="middle", y=0.5)
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

    with t2:
        st.markdown("##### 글로벌 기기 설치 지도")
        country_total = devices_df.groupby('수출국가')['수량환산'].sum().reset_index()
        fig_map = px.choropleth(
            country_total, locations="수출국가", locationmode="country names",
            color="수량환산", color_continuous_scale="Blues"
        )
        fig_map.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=480,
            geo=dict(bgcolor='rgba(0,0,0,0)', showframe=False)
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with t3:
        st.markdown("##### 주요 국가 및 고객사별 기기 공급 현황")
        pivot_df = devices_df.pivot_table(
            index=['수출국가', '고객'], 
            columns='기기 라인', 
            values='수량환산', 
            aggfunc='sum', 
            fill_value=0
        )
        st.dataframe(pivot_df.style.format("{:,.0f}").background_gradient(cmap="Blues"), use_container_width=True, height=450)

else:
    st.info("💡 `data/` 폴더 내에 엑셀 데이터 파일들이 업로드되어 있는지 확인해주세요.")
