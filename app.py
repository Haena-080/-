import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
import re

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="담당 국가별 기기 출고 현황",
    page_icon="📦",
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
                
            # 순수 완제품 기기만 필터링
            devices = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
            devices['기기 종류'] = devices['품명'].apply(classify_device_line)
            devices['연도'] = devices['연도'].astype(int)
            
            combined_dfs.append(devices)
        except Exception:
            continue
        
    return pd.concat(combined_dfs, ignore_index=True) if combined_dfs else None

# ---------------------------------------------------------
# 4. 메인 화면 구성
# ---------------------------------------------------------
st.title("📦 담당 국가별 기기 출고 현황 (다중 선택 가능)")

uploaded_files = st.sidebar.file_uploader("엑셀 데이터 파일 업로드", type=["xlsx"], accept_multiple_files=True)
df = load_data(uploaded_files)

if df is not None and len(df) > 0:
    # 다중 국가 선택 필터 (multiselect)
    all_countries = sorted([c for c in df['수출국가'].unique() if c and c != 'Nan'])
    selected_countries = st.multiselect(
        "🌍 담당 국가를 선택하세요 (여러 개 선택 가능):", 
        options=all_countries, 
        default=[]  # 기본값 비워둠 (아무것도 안 찍으면 전체 국가)
    )
    
    # 필터 적용
    filtered_df = df.copy()
    if selected_countries:
        filtered_df = filtered_df[filtered_df['수출국가'].isin(selected_countries)]
        display_title = ", ".join(selected_countries)
    else:
        display_title = "전체 국가"
        
    st.markdown("---")
    
    # 총 누적 수량 요약
    total_qty = int(filtered_df['수량환산'].sum())
    st.metric(label=f"[{display_title}] 총 기기 출고 수량", value=f"{total_qty:,} 대")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 1. 연도별 기기 출고 수량
    # ---------------------------------------------------------
    st.subheader("📅 1. 매년 어떤 기기가 몇 대 출고되었나요?")
    
    yearly_df = filtered_df.groupby(['연도', '기기 종류'])['수량환산'].sum().reset_index()
    
    if len(yearly_df) > 0:
        fig_year = px.bar(
            yearly_df, 
            x='연도', 
            y='수량환산', 
            color='기기 종류', 
            text_auto=',.0f',
            title=f"[{display_title}] 연도별 기기 출고 수량"
        )
        fig_year.update_layout(plot_bgcolor='white', height=380, xaxis=dict(type='category'))
        st.plotly_chart(fig_year, use_container_width=True)
        
        # 연도별 숫자 표
        year_pivot = filtered_df.pivot_table(
            index='연도', 
            columns='기기 종류', 
            values='수량환산', 
            aggfunc='sum', 
            fill_value=0,
            margins=True,
            margins_name="합계"
        )
        st.dataframe(year_pivot.style.format("{:,.0f}"), use_container_width=True)
    else:
        st.info("선택한 국가의 데이터가 없습니다.")

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 2. 월별 기기 출고 수량
    # ---------------------------------------------------------
    st.subheader("🗓️ 2. 월별로 기기가 몇 대 출고되었나요?")
    
    # 연도-월 칼럼 만들기
    filtered_df['연월'] = filtered_df.apply(lambda r: f"{int(r['연도'])}년 {int(r['월']):02d}월", axis=1)
    monthly_df = filtered_df.groupby(['연도', '월', '연월', '기기 종류'])['수량환산'].sum().reset_index().sort_values(by=['연도', '월'])
    
    if len(monthly_df) > 0:
        fig_month = px.bar(
            monthly_df, 
            x='연월', 
            y='수량환산', 
            color='기기 종류', 
            text_auto=',.0f',
            title=f"[{display_title}] 월별 기기 출고 수량"
        )
        fig_month.update_layout(plot_bgcolor='white', height=400)
        st.plotly_chart(fig_month, use_container_width=True)
        
        # 월별 숫자 표
        month_pivot = filtered_df.pivot_table(
            index=['연도', '월'], 
            columns='기기 종류', 
            values='수량환산', 
            aggfunc='sum', 
            fill_value=0,
            margins=True,
            margins_name="합계"
        )
        st.dataframe(month_pivot.style.format("{:,.0f}"), use_container_width=True)
    else:
        st.info("선택한 국가의 데이터가 없습니다.")

else:
    st.info("💡 `data/` 폴더에 엑셀 데이터 파일이 있거나 왼쪽 사이드바에 엑셀을 업로드해 주세요.")
