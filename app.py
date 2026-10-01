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
    page_title="아프리카 국가별 기기 출고 현황 (2018~2026.08)",
    page_icon="🗺️",
    layout="wide"
)

# ---------------------------------------------------------
# 2. 기기 플랫폼 세부 정제 및 분류 함수 (우선순위 적용)
# ---------------------------------------------------------
def classify_device_line(item_name):
    name = str(item_name).upper().replace(' ', '').replace('-', '').replace('_', '')
    
    # 1. Chemichroma (ichroma보다 먼저 체크 필수!)
    if 'CHEMICHROMA' in name:
        return 'Chemichroma'
    
    # 2. hemochroma 시리즈 (PLUS와 II 세부 분리)
    elif 'HEMOCHROMAPLUS' in name:
        return 'hemochroma PLUS'
    elif 'HEMOCHROMA' in name:
        return 'hemochroma II'
        
    # 3. AFIAS 세부 분류
    elif 'AFIAS10' in name:
        return 'AFIAS-10'
    elif 'AFIAS6' in name:
        return 'AFIAS-6'
    elif 'AFIAS3' in name:
        return 'AFIAS-3'
    elif 'AFIAS1' in name:
        return 'AFIAS-1'
    elif 'AFIAS' in name:
        return '기타 AFIAS'
    
    # 4. ichroma 세부 분류 (M2, M3, TRIAS, II/2, III/3)
    elif 'TRIAS' in name:
        return 'ichroma TRIAS'
    elif 'M3' in name:
        return 'ichroma M3'
    elif 'M2' in name:
        return 'ichroma M2'
    elif 'ICHROMA3' in name or 'ICHROMAIII' in name:
        return 'ichroma III'
    elif 'ICHROMA2' in name or 'ICHROMAII' in name or 'ICHROMA' in name:
        return 'ichroma II'
    
    # 5. Vet (동물용) 시리즈
    elif 'VET' in name:
        return 'Vet (동물용)'
    
    # 6. 기타 특정 기기 라인업
    elif 'CHAMBER' in name:
        return 'i-Chamber'
    elif 'ALCHEMIS' in name:
        return 'Alchemis'
    elif 'CBCHROMA' in name:
        return 'CBChroma'
    elif 'SPEEDREADER' in name:
        return 'Speed Reader'
    elif 'SYNCNEB' in name:
        return 'SyncNeb'
    elif 'AH600' in name:
        return 'AH600'
    else:
        return '기타 기기'

# ---------------------------------------------------------
# 3. 데이터 로드 및 정제 (2018 ~ 2026.08)
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
            
            # 헤더(Header) 행 자동 감지 로직
            header_idx = 3
            for idx, row in df_raw.iloc[:10].iterrows():
                row_str = " ".join([str(val) for val in row.values])
                if 'Level 1' in row_str or '수출국가' in row_str:
                    header_idx = idx
                    break
            
            df = df_raw.iloc[header_idx+1:].copy()
            df.columns = df_raw.iloc[header_idx].values
            
            # 컬럼명 띄어쓰기 정리
            df.columns = [str(c).strip() for c in df.columns]
            
            if 'Level 1' not in df.columns or 'Level 2' not in df.columns:
                continue

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
                df['연도'] = int(year_match.group()) if year_match else None

            # 월 추출
            if '월' in df.columns:
                df['월'] = pd.to_numeric(df['월'], errors='coerce').fillna(1).astype(int)
            elif '매출인식月' in df.columns:
                df['월'] = pd.to_numeric(df['매출인식月'], errors='coerce').fillna(1).astype(int)
            else:
                df['월'] = 1
                
            # 완제품 기기 필터링 (Level 1 == 완제품 & Level 2 == 기기)
            devices = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
            devices['기기 플랫폼'] = devices['품명'].apply(classify_device_line)
            
            combined_dfs.append(devices)
        except Exception:
            continue
        
    if not combined_dfs:
        return None
        
    final_df = pd.concat(combined_dfs, ignore_index=True)
    
    # 연도 결측치 보완 (최대한 2018~2026 범위 내 유지)
    final_df['연도'] = final_df['연도'].fillna(2026).astype(int)
    
    return final_df

# ---------------------------------------------------------
# 4. 메인 화면
# ---------------------------------------------------------
st.title("🗺️ 아프리카 국가별 기기 출고 현황 (2018 ~ 2026.08)")

uploaded_files = st.sidebar.file_uploader("엑셀 데이터 업로드", type=["xlsx"], accept_multiple_files=True)
df = load_data(uploaded_files)

if df is not None and len(df) > 0:
    
    # ---------------------------------------------------------
    # SECTION 1. 아프리카 지도 & 국가 선택
    # ---------------------------------------------------------
    st.subheader("🌐 1. 아프리카 지도에서 국가 클릭 또는 선택")
    st.caption("지도에서 원하는 국가 영토를 누르거나, 우측 드롭다운에서 국가를 선택하면 플랫폼별 출고 수량이 집계됩니다.")
    
    all_countries = sorted([c for c in df['수출국가'].unique() if c and c != 'Nan' and c != 'None'])
    
    col_map, col_select = st.columns([6, 4])
    
    # 지도용 누적 집계
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
            labels={'수량환산': '출고 수량(대)'}
        )
        fig_map.update_geos(
            showcountries=True, countrycolor="#B0BEC5",
            showland=True, landcolor="#F5F5F5",
            fitbounds="locations"
        )
        fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=420)
        
        # 지도 인터랙티브 선택 기능
        map_event = st.plotly_chart(
            fig_map, 
            use_container_width=True, 
            on_select="rerun", 
            selection_mode="points"
        )

    # 지도의 클릭 이벤트 감지
    clicked_country = None
    if map_event and "selection" in map_event and "points" in map_event["selection"]:
        points = map_event["selection"]["points"]
        if len(points) > 0 and "location" in points[0]:
            clicked_country = points[0]["location"]

    with col_select:
        # 클릭한 국가 자동 반영
        default_index = 0
        if clicked_country and clicked_country in all_countries:
            default_index = all_countries.index(clicked_country) + 1

        selected_country = st.selectbox(
            "🌍 조회 국가 선택:", 
            options=["전체 국가"] + all_countries, 
            index=default_index
        )
        
        # 선택된 국가 데이터 필터링
        country_df = df if selected_country == "전체 국가" else df[df['수출국가'] == selected_country]

        st.markdown(f"##### 📊 **[{selected_country}] 세부 플랫폼별 출고 현황 (2018~2026.08)**")
        platform_summary = country_df.groupby('기기 플랫폼')['수량환산'].sum().reset_index()
        platform_summary.columns = ['기기 플랫폼', '출고 수량 (대)']
        
        total_sum = platform_summary['출고 수량 (대)'].sum()
        
        st.dataframe(
            platform_summary.sort_values(by='출고 수량 (대)', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        st.success(f"**[{selected_country}] 총 누적 수량: {int(total_sum):,} 대**")

    st.markdown("---")

    # ---------------------------------------------------------
    # SECTION 2. 연도 선택 & 월별 출고 현황 (표 중심)
    # ---------------------------------------------------------
    st.subheader("🗓️ 2. 연도별 / 월별 세부 출고 현황표")
    
    # 2018~2026 연도 목록 전체 보장 (데이터에 존재하는 연도 + 2018~2026 전체 포함)
    data_years = set(country_df['연도'].unique())
    full_years = sorted(list(data_years.union(set(range(2018, 2027)))), reverse=True)
    
    selected_year = st.selectbox("📅 연도 선택 (2018~2026):", options=full_years, index=0)
    
    year_df = country_df[country_df['연도'] == selected_year]
    
    if len(year_df) > 0:
        month_pivot = year_df.pivot_table(
            index='월',
            columns='기기 플랫폼',
            values='수량환산',
            aggfunc='sum',
            fill_value=0
        )
        
        month_pivot = month_pivot.reindex(range(1, 13), fill_value=0)
        month_pivot.index = [f"{m}월" for m in month_pivot.index]
        month_pivot['월별 합계'] = month_pivot.sum(axis=1)
        
        st.markdown(f"##### 📋 **{selected_year}년도 [{selected_country}] 월별 기기 출고 현황표 (단위: 대)**")
        st.dataframe(
            month_pivot.style.format("{:,.0f}"),
            use_container_width=True
        )
    else:
        st.warning(f"{selected_year}년도에는 [{selected_country}]의 출고 데이터가 없습니다.")

else:
    st.info("💡 `data/` 폴더에 엑셀 데이터 파일이 있거나 왼쪽 사이드바에 엑셀을 업로드해 주세요.")
