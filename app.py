import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
import re

# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="아프리카 기기 출고 현황 대시보드 (2018~2026)",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------------
# 2. 기기 분류 함수 (대분류: 플랫폼 / 소분류: 기기 상세)
# ---------------------------------------------------------
def classify_device(item_name):
    name = str(item_name).upper().replace(' ', '').replace('-', '').replace('_', '')
    
    # 1. Chemichroma
    if 'CHEMICHROMA' in name:
        return 'Chemichroma', 'Chemichroma'
    
    # 2. hemochroma 시리즈
    elif 'HEMOCHROMAPLUS' in name:
        return 'hemochroma', 'hemochroma PLUS'
    elif 'HEMOCHROMA' in name:
        return 'hemochroma', 'hemochroma II'
        
    # 3. AFIAS 시리즈
    elif 'AFIAS10' in name:
        return 'AFIAS', 'AFIAS-10'
    elif 'AFIAS6' in name:
        return 'AFIAS', 'AFIAS-6'
    elif 'AFIAS3' in name:
        return 'AFIAS', 'AFIAS-3'
    elif 'AFIAS1' in name:
        return 'AFIAS', 'AFIAS-1'
    elif 'AFIAS' in name:
        return 'AFIAS', '기타 AFIAS'
    
    # 4. ichroma 시리즈
    elif 'TRIAS' in name:
        return 'ichroma', 'ichroma TRIAS'
    elif 'M3' in name:
        return 'ichroma', 'ichroma M3'
    elif 'M2' in name:
        return 'ichroma', 'ichroma M2'
    elif 'ICHROMA3' in name or 'ICHROMAIII' in name:
        return 'ichroma', 'ichroma III'
    elif 'ICHROMA2' in name or 'ICHROMAII' in name or 'ICHROMA' in name:
        return 'ichroma', 'ichroma II'
    
    # 5. Vet (동물용) 시리즈
    elif 'VET' in name:
        return 'Vet (동물용)', 'Vet (동물용)'
    
    # 6. 기타 특정 기기 라인업
    elif 'CHAMBER' in name:
        return 'i-Chamber', 'i-Chamber'
    elif 'ALCHEMIS' in name:
        return 'Alchemis', 'Alchemis'
    elif 'CBCHROMA' in name:
        return 'CBChroma', 'CBChroma'
    elif 'SPEEDREADER' in name:
        return 'Speed Reader', 'Speed Reader'
    elif 'SYNCNEB' in name:
        return 'SyncNeb', 'SyncNeb'
    elif 'AH600' in name:
        return 'AH600', 'AH600'
    else:
        return '기타', '기타 기기'

# ---------------------------------------------------------
# 3. 데이터 로드 및 정제
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
            
            df['Level 1'] = df['Level 1'].astype(str).str.strip()
            df['Level 2'] = df['Level 2'].astype(str).str.strip()
            df['수출국가'] = df['수출국가'].astype(str).str.strip().str.title()
            df['수량환산'] = pd.to_numeric(df['수량환산'], errors='coerce').fillna(0)
            
            # 거래처/회사 컬럼 확인
            if '거래처' in df.columns:
                df['회사'] = df['거래처'].astype(str).str.strip()
            elif '거래처명' in df.columns:
                df['회사'] = df['거래처명'].astype(str).str.strip()
            elif '고객사' in df.columns:
                df['회사'] = df['고객사'].astype(str).str.strip()
            else:
                df['회사'] = '미지정'
            
            # 연도 파싱
            if '연도' in df.columns:
                df['연도'] = pd.to_numeric(df['연도'], errors='coerce')
            elif '매출인식年' in df.columns:
                df['연도'] = pd.to_numeric(df['매출인식年'], errors='coerce')
            else:
                year_match = re.search(r'20\d{2}', file_name)
                df['연도'] = int(year_match.group()) if year_match else 2026
                
            # 월 파싱
            if '월' in df.columns:
                df['월'] = pd.to_numeric(df['월'], errors='coerce').fillna(1).astype(int)
            elif '매출인식月' in df.columns:
                df['월'] = pd.to_numeric(df['매출인식月'], errors='coerce').fillna(1).astype(int)
            else:
                df['월'] = 1
                
            # 완제품 기기 필터링 (Level 1 == 완제품 & Level 2 == 기기)
            devices = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
            
            # 플랫폼 및 상세 기기 분류 적용
            classified = devices['품명'].apply(classify_device)
            devices['기기 플랫폼'] = [c[0] for c in classified]
            devices['기기 상세'] = [c[1] for c in classified]
            devices['연도'] = devices['연도'].fillna(2026).astype(int)
            
            combined_dfs.append(devices)
        except Exception:
            continue
        
    return pd.concat(combined_dfs, ignore_index=True) if combined_dfs else None

# ---------------------------------------------------------
# 4. 메인 대시보드 화면
# ---------------------------------------------------------
st.title("📊 아프리카 국가별/기기별 출고 현황 대시보드")

uploaded_files = st.sidebar.file_uploader("📂 엑셀 파일 업로드", type=["xlsx"], accept_multiple_files=True)
df = load_data(uploaded_files)

if df is not None and len(df) > 0:
    
    # ---------------------------------------------------------
    # 다중 선택 (Multi-select) 필터 사이드바
    # ---------------------------------------------------------
    st.sidebar.header("🔍 검색 및 다중 선택 필터")
    
    # 1. 연도 필터 (2018~2026 전체 표시 보장)
    existing_years = set(df['연도'].dropna().unique())
    all_years = sorted(list(existing_years.union(set(range(2018, 2027)))), reverse=True)
    selected_years = st.sidebar.multiselect("📅 연도 선택", options=all_years, default=sorted(list(existing_years), reverse=True))
    
    # 2. 월 필터
    all_months = list(range(1, 13))
    selected_months = st.sidebar.multiselect("🗓️ 월 선택", options=all_months, default=all_months, format_func=lambda x: f"{x}월")
    
    # 3. 국가 필터
    all_countries = sorted([c for c in df['수출국가'].unique() if c and c != 'Nan'])
    selected_countries = st.sidebar.multiselect("🌍 국가 선택", options=all_countries, default=all_countries)
    
    # 4. 회사 필터
    all_companies = sorted([c for c in df['회사'].unique() if c and c != 'nan'])
    selected_companies = st.sidebar.multiselect("🏢 회사(거래처) 선택", options=all_companies, default=all_companies)
    
    # 5. 기기 플랫폼 필터 (대분류)
    all_platforms = sorted(list(df['기기 플랫폼'].unique()))
    selected_platforms = st.sidebar.multiselect("🔬 기기 플랫폼(대분류) 선택", options=all_platforms, default=all_platforms)
    
    # 6. 기기 상세 필터 (소분류)
    filtered_details_options = sorted(list(df[df['기기 플랫폼'].isin(selected_platforms)]['기기 상세'].unique()))
    selected_details = st.sidebar.multiselect("⚙️ 기기 상세(소분류) 선택", options=filtered_details_options, default=filtered_details_options)

    # ---------------------------------------------------------
    # 필터 조건에 따른 데이터 추출
    # ---------------------------------------------------------
    filtered_df = df[
        (df['연도'].isin(selected_years)) &
        (df['월'].isin(selected_months)) &
        (df['수출국가'].isin(selected_countries)) &
        (df['회사'].isin(selected_companies)) &
        (df['기기 플랫폼'].isin(selected_platforms)) &
        (df['기기 상세'].isin(selected_details))
    ]

    # 요약 카드 (KPI Metrics)
    m1, m2, m3, m4 = st.columns(4)
    total_qty = filtered_df['수량환산'].sum()
    country_count = filtered_df['수출국가'].nunique()
    company_count = filtered_df['회사'].nunique()
    device_count = filtered_df['기기 상세'].nunique()
    
    m1.metric("총 출고 수량", f"{int(total_qty):,} 대")
    m2.metric("선택 국가 수", f"{country_count} 개국")
    m3.metric("선택 회사 수", f"{company_count} 개사")
    m4.metric("기기 모델 종류", f"{device_count} 종")

    st.markdown("---")

    # ---------------------------------------------------------
    # 지도 및 플랫폼/기기 상세 집계
    # ---------------------------------------------------------
    col_map, col_summary = st.columns([6, 4])
    
    with col_map:
        st.subheader("🌐 아프리카 지도 분포")
        map_df = filtered_df.groupby('수출국가')['수량환산'].sum().reset_index()
        
        fig_map = px.choropleth(
            map_df,
            locationmode='country names',
            locations='수출국가',
            color='수량환산',
            hover_name='수출국가',
            color_continuous_scale='Purples',
            scope='africa',
            labels={'수량환산': '출고 수량(대)'}
        )
        fig_map.update_geos(
            showcountries=True, countrycolor="#B0BEC5",
            showland=True, landcolor="#F5F5F5",
            fitbounds="locations"
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=450)
        st.plotly_chart(fig_map, use_container_width=True)

    with col_summary:
        st.subheader("📋 기기 상세 집계표")
        detail_summary = filtered_df.groupby(['기기 플랫폼', '기기 상세'])['수량환산'].sum().reset_index()
        detail_summary.columns = ['플랫폼', '기기 상세 모델', '출고 수량 (대)']
        detail_summary = detail_summary.sort_values(by='출고 수량 (대)', ascending=False)
        
        st.dataframe(
            detail_summary,
            use_container_width=True,
            hide_index=True,
            height=380
        )

    st.markdown("---")

    # ---------------------------------------------------------
    # 세부 크로스탭 분석 피벗 테이블
    # ---------------------------------------------------------
    st.subheader("📑 조건별 세부 출고 피벗 테이블")
    
    view_option = st.radio(
        "표시할 행(Row) 기준 선택:",
        ["국가별 x 기기 상세", "회사별 x 기기 상세", "월별 x 기기 상세", "연도별 x 기기 상세"],
        horizontal=True
    )
    
    if view_option == "국가별 x 기기 상세":
        row_col = '수출국가'
    elif view_option == "회사별 x 기기 상세":
        row_col = '회사'
    elif view_option == "월별 x 기기 상세":
        row_col = '월'
    else:
        row_col = '연도'

    if len(filtered_df) > 0:
        pivot_df = filtered_df.pivot_table(
            index=row_col,
            columns='기기 상세',
            values='수량환산',
            aggfunc='sum',
            fill_value=0
        )
        pivot_df['총 합계'] = pivot_df.sum(axis=1)
        pivot_df = pivot_df.sort_values(by='총 합계', ascending=False)
        
        if row_col == '월':
            pivot_df.index = [f"{m}월" for m in pivot_df.index]
            
        st.dataframe(pivot_df.style.format("{:,.0f}"), use_container_width=True)
    else:
        st.warning("선택한 필터 조건에 해당하는 데이터가 없습니다.")

else:
    st.info("💡 `data/` 폴더에 엑셀 데이터 파일이 있거나 왼쪽 사이드바에 엑셀을 업로드해 주세요.")
