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
    page_title="아프리카 국가별 & 연도/월별 기기 출고 현황",
    page_icon="📋",
    layout="wide"
)

# ---------------------------------------------------------
# 2. 기기 라인업 분류 함수
# ---------------------------------------------------------
def classify_device_line(item_name):
    name = str(item_name).upper()
    if 'AFIAS' in name:
        return 'AFIAS'
    elif 'ICHROMA' in name and 'CHEMICHROMA' not in name:
        return 'ichroma'
    elif 'CHEMICHROMA' in name:
        return 'Chemichroma'
    elif 'HEMOCHROMA' in name:
        return 'hemochroma'
    elif 'VET' in name:
        return 'Vet (동물용)'
    elif 'CHAMBER' in name or 'I-CHAMBER' in name:
        return 'i-Chamber'
    elif 'THERMO' in name:
        return 'Thermo-block'
    else:
        return '기타 기기'

# ---------------------------------------------------------
# 3. 데이터 로드
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
            
            # 연도 추출
            if '연도' in df.columns:
                df['연도'] = pd.to_numeric(df['연도'], errors='coerce')
            elif '매출인식年' in df.columns:
                df['연도'] = pd.to_numeric(df['매출인식年'], errors='coerce')
            else:
                year_match = re.search(r'20\d{2}', file_name)
                df['연도'] = int(year_match.group()) if year_match else 2026
                
            # 월 추출
            if '월' in df.columns:
                df['월'] = pd.to_numeric(df['월'], errors='coerce').fillna(1).astype(int)
            elif '매출인식月' in df.columns:
                df['월'] = pd.to_numeric(df['매출인식月'], errors='coerce').fillna(1).astype(int)
            else:
                df['월'] = 1
                
            # 완제품 기기만 필터링
            devices = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
            devices['기기 플랫폼'] = devices['품명'].apply(classify_device_line)
            devices['연도'] = devices['연도'].astype(int)
            
            combined_dfs.append(devices)
        except Exception:
            continue
        
    return pd.concat(combined_dfs, ignore_index=True) if combined_dfs else None

# ---------------------------------------------------------
# 4. 메인 대시보드 화면
# ---------------------------------------------------------
st.title("📋 아프리카 국가별 & 연도/월별 기기 출고 현황")

uploaded_files = st.sidebar.file_uploader("엑셀 데이터 업로드", type=["xlsx"], accept_multiple_files=True)
df = load_data(uploaded_files)

if df is not None and len(df) > 0:
    
    # ---------------------------------------------------------
    # SECTION 1. 아프리카 지도 & 국가 선택
    # ---------------------------------------------------------
    st.subheader("🗺️ 1. 아프리카 지도에서 국가 선택")
    st.caption("지도의 국가를 선택하거나 아래 Dropdown에서 국가를 선택하면, 해당 국가의 기기 플랫폼별 출고 수량이 표로 집계됩니다.")
    
    all_countries = sorted([c for c in df['수출국가'].unique() if c and c != 'Nan'])
    
    col_map, col_select = st.columns([6, 4])
    
    # 지도 데이터 준비
    map_df = df.groupby('수출국가')['수량환산'].sum().reset_index()
    
    with col_map:
        fig_map = px.choropleth(
            map_df,
            locationmode='country names',
            locations='수출국가',
            color='수량환산',
            hover_name='수출국가',
            color_continuous_scale='Purples',
            scope='africa',
            title=""
        )
        fig_map.update_geos(
            showcountries=True, countrycolor="#ced4da",
            showland=True, landcolor="#f8f9fa",
            fitbounds="locations"
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=380)
        
        # 지도에서 선택 capture (on_select 사용)
        map_event = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun", selection_mode="points")

    # 선택된 국가 감지
    clicked_country = None
    if map_event and "selection" in map_event and "points" in map_event["selection"]:
        points = map_event["selection"]["points"]
        if len(points) > 0 and "location" in points[0]:
            clicked_country = points[0]["location"]

    with col_select:
        # 지도를 클릭했으면 클릭한 국가를 선택, 없으면 기본 드롭다운 사용
        default_index = 0
        if clicked_country and clicked_country in all_countries:
            default_index = all_countries.index(clicked_country) + 1

        selected_country = st.selectbox(
            "🌍 조회 대상 국가 선택:", 
            options=["전체 국가"] + all_countries, 
            index=default_index
        )
        
        # 선택 국가 필터링
        if selected_country != "전체 국가":
            country_df = df[df['수출국가'] == selected_country]
        else:
            country_df = df.copy()

        # 기기 플랫폼별 누적 현황 표 표시
        st.markdown(f"##### 📊 **[{selected_country}] 기기 플랫폼별 누적 출고 수량**")
        platform_summary = country_df.groupby('기기 플랫폼')['수량환산'].sum().reset_index()
        platform_summary.columns = ['기기 플랫폼', '출고 수량 (대)']
        
        total_sum = platform_summary['출고 수량 (대)'].sum()
        
        st.dataframe(
            platform_summary.sort_values(by='출고 수량 (대)', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        st.success(f"**총 누적 출고 수량: {int(total_sum):,} 대**")

    st.markdown("---")

    # ---------------------------------------------------------
    # SECTION 2. 연도 선택 & 월별 출고 현황 (표 중심)
    # ---------------------------------------------------------
    st.subheader("🗓️ 2. 연도별 / 월별 기기 출고 현황 (표 형식)")
    st.caption("조회하고 싶은 연도를 선택하면, 선택된 국가에서 **매월 어떤 기기가 몇 대 출고되었는지** 월별 표로 확인하실 수 있습니다.")
    
    available_years = sorted([int(y) for y in country_df['연도'].unique()], reverse=True)
    selected_year = st.selectbox("📅 연도 선택:", options=available_years, index=0)
    
    # 선택된 연도의 데이터 필터링
    year_df = country_df[country_df['연도'] == selected_year]
    
    if len(year_df) > 0:
        # 월별 - 기기 플랫폼 피벗 테이블 생성
        month_pivot = year_df.pivot_table(
            index='월',
            columns='기기 플랫폼',
            values='수량환산',
            aggfunc='sum',
            fill_value=0
        )
        
        # 1월~12월 모든 월 표시되도록 reindex
        month_pivot = month_pivot.reindex(range(1, 13), fill_value=0)
        month_pivot.index = [f"{m}월" for m in month_pivot.index]
        
        # 합계 행 및 열 추가
        month_pivot['월별 합계'] = month_pivot.sum(axis=1)
        
        # 소수점 제거 및 정수 포맷팅
        st.markdown(f"##### 📋 **{selected_year}년도 [{selected_country}] 월별 기기 출고 현황표 (단위: 대)**")
        st.dataframe(
            month_pivot.style.format("{:,.0f}").highlight_max(axis=0, color="#e6f4ea"),
            use_container_width=True
        )
    else:
        st.warning(f"{selected_year}년도에는 [{selected_country}]의 출고 데이터가 없습니다.")

else:
    st.info("💡 `data/` 폴더에 엑셀 데이터 파일이 있거나 왼쪽 사이드바에 엑셀을 업로드해 주세요.")
