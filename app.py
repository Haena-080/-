import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(
    page_title="글로벌 기기 출고 및 고객사 분석 플랫폼",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 글로벌 기기 출고 및 고객사 분석 플랫폼")
st.markdown("매출 DB 기반 **전 세계 기기 설치 지도 시각화** 및 **국가/고객사별 기기 라인업 분석**")

# 기기 라인업 자동 분류 함수
def classify_device_line(item_name):
    name = str(item_name).upper()
    if 'AFIAS' in name:
        return 'AFIAS 라인'
    elif 'ICHROMA' in name:
        return 'ichroma 라인'
    elif 'HEMOCHROMA' in name:
        return 'hemochroma 라인'
    elif 'VET' in name:
        return 'Vet (동물용) 라인'
    elif 'CHAMBER' in name or 'I-CHAMBER' in name:
        return 'i-Chamber (배양기)'
    elif 'THERMO' in name:
        return 'Thermo-block'
    else:
        return '기타 기기'

# 2. 파일 업로더
uploaded_file = st.file_uploader("최신 매출 DB 엑셀 파일 (.xlsx)을 업로드하세요", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 데이터 읽기
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        
        # 헤더 정돈
        df = df_raw.iloc[4:].copy()
        df.columns = df_raw.iloc[3].values
        
        # 전처리
        df['Level 1'] = df['Level 1'].astype(str).str.strip()
        df['Level 2'] = df['Level 2'].astype(str).str.strip()
        df['수출국가'] = df['수출국가'].astype(str).str.strip().str.title()  # 지도 매핑용 Title case
        df['고객'] = df['고객'].astype(str).str.strip()
        df['담당자'] = df['담당자'].astype(str).str.strip()
        df['팀 분류'] = df['팀 분류'].astype(str).str.strip()
        df['매출인식月'] = pd.to_numeric(df['매출인식月'], errors='coerce')
        df['수량환산'] = pd.to_numeric(df['수량환산'], errors='coerce').fillna(0)
        
        # 완제품 기기 필터링 및 기기 라인 분류
        devices_df = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
        devices_df['기기 라인'] = devices_df['품명'].apply(classify_device_line)
        
        st.success(f"✅ 데이터 분석 완료! (총 {len(devices_df):,} 건의 완제품 기기 출고 데이터)")
        
        # 3. 사이드바 영업 필터
        st.sidebar.header("🔍 영업 분석 필터")
        
        teams = sorted([t for t in devices_df['팀 분류'].unique() if t and t != 'nan'])
        selected_teams = st.sidebar.multiselect("담당 팀 선택", options=teams, default=[])
        if selected_teams:
            devices_df = devices_df[devices_df['팀 분류'].isin(selected_teams)]
            
        managers = sorted([m for m in devices_df['담당자'].unique() if m and m != 'nan'])
        selected_managers = st.sidebar.multiselect("영업 담당자 선택", options=managers, default=[])
        if selected_managers:
            devices_df = devices_df[devices_df['담당자'].isin(selected_managers)]
            
        countries = sorted(devices_df['수출국가'].unique())
        selected_countries = st.sidebar.multiselect("수출 국가 선택", options=countries, default=[])
        if selected_countries:
            devices_df = devices_df[devices_df['수출국가'].isin(selected_countries)]
            
        device_lines = sorted(devices_df['기기 라인'].unique())
        selected_lines = st.sidebar.multiselect("기기 라인 선택", options=device_lines, default=[])
        if selected_lines:
            devices_df = devices_df[devices_df['기기 라인'].isin(selected_lines)]

        month_cols = sorted([int(m) for m in devices_df['매출인식月'].dropna().unique()])
        
        # 4. 주요 요약 지표
        st.subheader("📌 영업 핵심 KPI")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("진출 국가 수", f"{devices_df['수출국가'].nunique():,} 개국")
        col2.metric("총 거래 고객사 수", f"{devices_df['고객'].nunique():,} 개사")
        col3.metric("총 기기 출고 수량", f"{int(devices_df['수량환산'].sum()):,} 대")
        col4.metric("집계 월 범위", f"{min(month_cols)}월 ~ {max(month_cols)}월")
        
        st.write("---")
        
        # 5. 분석 탭
        tab1, tab2, tab3, tab4 = st.tabs([
            "🗺️ 글로벌 기기 설치 지도", 
            "👥 고객사별 기기 믹스", 
            "📆 월별/누적 출고 추이", 
            "🔎 국가별 상세 드릴다운"
        ])
        
        # TAB 1: 지도 시각화 (요청하신 기능)
        with tab1:
            st.subheader("🗺️ 전 세계 국가별 기기 출고 및 설치 분포 지도")
            
            # 국가별 집계
            country_map_df = devices_df.groupby(['수출국가', '기기 라인'])['수량환산'].sum().reset_index()
            country_total = devices_df.groupby('수출국가')['수량환산'].sum().reset_index()
            country_total.rename(columns={'수량환산': '총 기기 출고량'}, inplace=True)
            
            map_style = st.radio("지도 시각화 스타일 선택", ["색상 음영 지도 (Choropleth)", "비례 원형 버블 지도 (Bubble Map)"], horizontal=True)
            scope = st.selectbox("조회 지역 선택", ["world", "asia", "europe", "africa", "north america", "south america"])
            
            if "색상 음영" in map_style:
                fig_map = px.choropleth(
                    country_total,
                    locations="수출국가",
                    locationmode="country names",
                    color="총 기기 출고량",
                    hover_name="수출국가",
                    color_continuous_scale="Purples", # 이미지 느낌의 퍼플 스케일
                    title="국가별 총 기기 출고량 음영 지도",
                    scope=scope
                )
            else:
                fig_map = px.scatter_geo(
                    country_map_df,
                    locations="수출국가",
                    locationmode="country names",
                    size="수량환산",
                    color="기기 라인",
                    hover_name="수출국가",
                    size_max=35,
                    title="국가/기기 라인별 비례 버블 분포 지도",
                    scope=scope
                )
                
            fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=550)
            st.plotly_chart(fig_map, use_container_width=True)
            
        # TAB 2: 고객사 믹스
        with tab2:
            st.subheader("고객사별 기기 라인업 출고 수량 및 비중")
            
            cust_line_pivot = devices_df.pivot_table(
                index=['수출국가', '고객'],
                columns='기기 라인',
                values='수량환산',
                aggfunc='sum',
                fill_value=0
            )
            cust_line_pivot['합계'] = cust_line_pivot.sum(axis=1)
            cust_line_pivot = cust_line_pivot.sort_values(by='합계', ascending=False)
            
            st.dataframe(cust_line_pivot.style.format("{:,.0f}"), use_container_width=True)
            
            st.subheader("상위 15개 고객사의 기기 라인업 믹스")
            top_15_cust = cust_line_pivot.head(15).drop(columns=['합계']).reset_index()
            top_15_melted = top_15_cust.melt(id_vars=['수출국가', '고객'], var_name='기기 라인', value_name='수량')
            
            fig_mix = px.bar(
                top_15_melted,
                x='고객',
                y='수량',
                color='기기 라인',
                title="상위 고객사별 기기 라인 출고 분포 (Stacked Bar)",
                text_auto=',.0f'
            )
            fig_mix.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_mix, use_container_width=True)
            
        # TAB 3: 월별/누적 추이
        with tab3:
            st.subheader("고객사별 월별 단독 및 누적 출고량")
            
            cust_monthly = devices_df.pivot_table(
                index=['수출국가', '고객'],
                columns='매출인식月',
                values='수량환산',
                aggfunc='sum',
                fill_value=0
            )
            
            month_names = [f"{int(m)}월" for m in sorted(cust_monthly.columns)]
            cust_monthly.columns = month_names
            cust_monthly['총 누적 출고량'] = cust_monthly.sum(axis=1)
            cust_monthly = cust_monthly.sort_values(by='총 누적 출고량', ascending=False)
            
            cust_cum = cust_monthly[month_names].cumsum(axis=1)
            cust_cum['최종 누적량'] = cust_monthly['총 누적 출고량']
            
            st.markdown("##### 1. 고객사별 월별 출고량 (대)")
            st.dataframe(cust_monthly.style.format("{:,.0f}"), use_container_width=True)
            
            st.markdown("##### 2. 고객사별 월별 누적 출고량 (대)")
            st.dataframe(cust_cum.style.format("{:,.0f}"), use_container_width=True)
            
        # TAB 4: 국가별 상세
        with tab4:
            st.subheader("특정 국가 내 고객사별 기기 설치/출고 현황 드릴다운")
            target_country = st.selectbox("분석할 국가를 선택하세요", options=countries)
            
            country_df = devices_df[devices_df['수출국가'] == target_country]
            
            if len(country_df) > 0:
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**[{target_country}] 기기 라인업 비중**")
                    fig_pie = px.pie(country_df, names='기기 라인', values='수량환산', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                with c2:
                    st.write(f"**[{target_country}] 고객사별 기기 출고량**")
                    cust_bar = country_df.groupby(['고객', '기기 라인'])['수량환산'].sum().reset_index()
                    fig_cbar = px.bar(cust_bar, x='고객', y='수량환산', color='기기 라인', barmode='group', text_auto=',.0f')
                    st.plotly_chart(fig_cbar, use_container_width=True)
                    
                st.write(f"**[{target_country}] 상세 출고 품목 내역**")
                st.dataframe(
                    country_df[['매출인식月', '고객', '품번', '품명', '기기 라인', '수량환산', '담당자']]
                    .sort_values(by=['고객', '매출인식月']),
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
else:
    st.info("👆 상단의 [Browse files] 버튼을 눌러 매출 DB 엑셀 파일을 업로드해주세요.")
