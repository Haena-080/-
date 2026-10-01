import streamlit as st
import pandas as pd
import pydeck as pdk
import glob
import os
import re

# ---------------------------------------------------------
# 1. 페이지 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="아프리카 기기 출고 현황 (2018~2026.08)",
    page_icon="🗺️",
    layout="wide"
)

# ---------------------------------------------------------
# 2. 아프리카 주요 국가 위도/경도 좌표 데이터베이스
# ---------------------------------------------------------
AFRICA_COORDS = {
    "Ghana": {"lat": 7.9465, "lon": -1.0232},
    "Nigeria": {"lat": 9.0820, "lon": 8.6753},
    "Kenya": {"lat": -0.0236, "lon": 37.9062},
    "Ethiopia": {"lat": 9.1450, "lon": 40.4897},
    "Egypt": {"lat": 26.8206, "lon": 30.8025},
    "South Africa": {"lat": -30.5595, "lon": 22.9375},
    "Tanzania": {"lat": -6.3690, "lon": 34.8888},
    "Uganda": {"lat": 1.3733, "lon": 32.2903},
    "Algeria": {"lat": 28.0339, "lon": 1.6596},
    "Morocco": {"lat": 31.7917, "lon": -7.0926},
    "Senegal": {"lat": 14.4974, "lon": -14.4524},
    "Cote D'Ivoire": {"lat": 7.5400, "lon": -5.5471},
    "Ivory Coast": {"lat": 7.5400, "lon": -5.5471},
    "Cameroon": {"lat": 3.8480, "lon": 11.5021},
    "Rwanda": {"lat": -1.9403, "lon": 29.8739},
    "Angola": {"lat": -11.2027, "lon": 17.8739},
    "Sudan": {"lat": 12.8628, "lon": 30.2176},
    "Zambia": {"lat": -13.1339, "lon": 27.8493},
    "Zimbabwe": {"lat": -19.0154, "lon": 29.1549},
    "Tunisia": {"lat": 33.8869, "lon": 9.5375},
    "Libya": {"lat": 26.3351, "lon": 17.2283},
    "Madagascar": {"lat": -18.7669, "lon": 46.8691},
    "Mozambique": {"lat": -18.6657, "lon": 35.5296},
    "Mali": {"lat": 17.5707, "lon": -3.9962},
    "DR Congo": {"lat": -4.0383, "lon": 21.7587},
    "Congo": {"lat": -0.2280, "lon": 15.8277}
}

# ---------------------------------------------------------
# 3. 기기 라인업 분류 함수
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
# 4. 데이터 로드 (2018 ~ 2026.08)
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
# 5. 메인 화면
# ---------------------------------------------------------
st.title("🗺️ 아프리카 3D 기기 출고 현황 (2018 ~ 2026.08)")

uploaded_files = st.sidebar.file_uploader("엑셀 데이터 업로드", type=["xlsx"], accept_multiple_files=True)
df = load_data(uploaded_files)

if df is not None and len(df) > 0:
    
    # ---------------------------------------------------------
    # SECTION 1. Pydeck 3D 지도 표현
    # ---------------------------------------------------------
    st.subheader("🌐 1. 아프리카 국가별 3D 입체 출고 지도 (2018~2026.08 누적)")
    st.caption("2018년부터 2026년 8월까지의 총 출고 수량이 높낮이와 색상으로 지도에 3D 기둥으로 나타납니다.")
    
    map_summary = df.groupby('수출국가')['수량환산'].sum().reset_index()
    
    map_summary['lat'] = map_summary['수출국가'].apply(lambda c: AFRICA_COORDS.get(c, {}).get('lat', 0.0))
    map_summary['lon'] = map_summary['수출국가'].apply(lambda c: AFRICA_COORDS.get(c, {}).get('lon', 0.0))
    map_summary = map_summary[(map_summary['lat'] != 0.0) & (map_summary['lon'] != 0.0)]
    
    col_map_view, col_detail_view = st.columns([6, 4])
    
    with col_map_view:
        layer = pdk.Layer(
            "ColumnLayer",
            data=map_summary,
            get_position=["lon", "lat"],
            get_elevation="수량환산",
            elevation_scale=1200,
            radius=120000,
            get_fill_color="[수량환산 * 5, 100, 220, 200]",
            pickable=True,
            auto_highlight=True,
        )
        
        view_state = pdk.ViewState(
            latitude=2.0,
            longitude=16.0,
            zoom=2.8,
            pitch=45,
            bearing=0
        )
        
        r = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "국가: {수출국가}\n누적 출고 수량: {수량환산} 대"},
            map_style="mapbox://styles/mapbox/light-v10"
        )
        
        st.pydeck_chart(r)

    with col_detail_view:
        all_countries = sorted([c for c in df['수출국가'].unique() if c and c != 'Nan'])
        selected_country = st.selectbox("🌍 상세 조회 국가 선택:", options=["전체 국가"] + all_countries, index=0)
        
        country_df = df if selected_country == "전체 국가" else df[df['수출국가'] == selected_country]

        st.markdown(f"##### 📊 **[{selected_country}] 기기 플랫폼별 누적 현황 (2018~2026.08)**")
        platform_summary = country_df.groupby('기기 플랫폼')['수량환산'].sum().reset_index()
        platform_summary.columns = ['기기 플랫폼', '출고 수량 (대)']
        
        total_sum = platform_summary['출고 수량 (대)'].sum()
        
        st.dataframe(
            platform_summary.sort_values(by='출고 수량 (대)', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        st.info(f"**[{selected_country}] 총 누적 수량: {int(total_sum):,} 대**")

    st.markdown("---")

    # ---------------------------------------------------------
    # SECTION 2. 연도 선택 & 월별 출고 현황 (표 중심)
    # ---------------------------------------------------------
    st.subheader("🗓️ 2. 연도별 / 월별 기기 출고 현황표")
    
    # 2018~2026 연도 정렬
    available_years = sorted([int(y) for y in country_df['연도'].unique()], reverse=True)
    selected_year = st.selectbox("📅 연도 선택 (2018~2026):", options=available_years, index=0)
    
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
