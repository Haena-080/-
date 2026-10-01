import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="국가별 기기 출고 누적 분석 플랫폼",
    page_icon="📊",
    layout="wide"
)

st.title("📊 국가별 기기 출고 누적 분석 플랫폼")
st.markdown("매달 매출 DB 엑셀 파일을 업로드하면 **국가별/월별 기기 출고량 및 누적 수치**를 자동으로 집계합니다.")

# 2. 파일 업로더
uploaded_file = st.file_uploader("최신 매출 DB 엑셀 파일 (.xlsx)을 업로드하세요", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 데이터 읽기
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = xls.sheet_names[0]
        df_raw = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        
        # 헤더 정돈 (4번째 행이 실제 칼럼명)
        df = df_raw.iloc[4:].copy()
        df.columns = df_raw.iloc[3].values
        
        # 전처리
        df['Level 1'] = df['Level 1'].astype(str).str.strip()
        df['Level 2'] = df['Level 2'].astype(str).str.strip()
        df['수출국가'] = df['수출국가'].astype(str).str.strip()
        df['매출인식月'] = pd.to_numeric(df['매출인식月'], errors='coerce')
        df['수량환산'] = pd.to_numeric(df['수량환산'], errors='coerce').fillna(0)
        
        # 완제품 & 기기 데이터만 추출
        devices_df = df[(df['Level 1'] == '완제품') & (df['Level 2'] == '기기')].copy()
        
        st.success(f"✅ 데이터 로드 완료! (총 {len(devices_df):,} 건의 기기 출고 내역)")
        
        # 사이드바 필터
        st.sidebar.header("🔍 필터 옵션")
        selected_countries = st.sidebar.multiselect(
            "국가 선택 (미선택 시 전체)",
            options=sorted(devices_df['수출국가'].unique()),
            default=[]
        )
        
        selected_products = st.sidebar.multiselect(
            "제품군 선택 (미선택 시 전체)",
            options=sorted(devices_df['제품군'].dropna().unique()),
            default=[]
        )
        
        # 필터링 적용
        filtered_df = devices_df.copy()
        if selected_countries:
            filtered_df = filtered_df[filtered_df['수출국가'].isin(selected_countries)]
        if selected_products:
            filtered_df = filtered_df[filtered_df['제품군'].isin(selected_products)]
            
        # 월별 피벗 테이블 생성
        pivot_monthly = filtered_df.pivot_table(
            index='수출국가',
            columns='매출인식月',
            values='수량환산',
            aggfunc='sum',
            fill_value=0
        )
        
        # 컬럼 정렬 (월 순서)
        month_cols = sorted([c for c in pivot_monthly.columns if isinstance(c, (int, float)) and not pd.isna(c)])
        pivot_monthly = pivot_monthly[month_cols]
        pivot_monthly.columns = [f"{int(m)}월" for m in month_cols]
        
        # 월별 합계 및 누적 계산
        pivot_monthly['총 출고량'] = pivot_monthly.sum(axis=1)
        pivot_monthly = pivot_monthly.sort_values(by='총 출고량', ascending=False)
        
        # 누적 집계 테이블 (Cumsum)
        pivot_cum = pivot_monthly.drop(columns=['총 출고량']).cumsum(axis=1)
        pivot_cum['최종 누적량'] = pivot_monthly['총 출고량']
        
        # 3. 주요 요약 지표 (KPI)
        st.subheader("📌 주요 지표 (KPI)")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("총 출고 국가 수", f"{len(pivot_monthly)} 개국")
        col2.metric("총 기기 출고 수량", f"{int(pivot_monthly['총 출고량'].sum()):,} 대")
        
        top_country = pivot_monthly.index[0] if len(pivot_monthly) > 0 else "-"
        top_qty = pivot_monthly['총 출고량'].iloc[0] if len(pivot_monthly) > 0 else 0
        col3.metric("최대 출고 국가", top_country, f"{int(top_qty):,} 대")
        col4.metric("집계 월 범위", f"{int(min(month_cols))}월 ~ {int(max(month_cols))}월")
        
        st.write("---")
        
        # 4. 시각화 탭 분리
        tab1, tab2, tab3 = st.tabs(["📈 월별 누적 추이 차트", "📋 상세 데이터 테이블", "📊 국가별 순위 차트"])
        
        with tab1:
            st.subheader("국가별 기기 출고 누적 추이")
            # 누적 데이터 재구성 (Plotly 선 그래프용)
            cum_plot_df = pivot_cum.drop(columns=['최종 누적량']).reset_index().melt(
                id_vars='수출국가', var_name='월', value_name='누적 출고량'
            )
            
            top_10_countries = pivot_monthly.head(10).index.tolist()
            show_top = st.checkbox("상위 10개국만 보기", value=True)
            if show_top:
                cum_plot_df = cum_plot_df[cum_plot_df['수출국가'].isin(top_10_countries)]
                
            fig_line = px.line(
                cum_plot_df, x='월', y='누적 출고량', color='수출국가', markers=True,
                title="월별 기기 출고 누적 그래프"
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
        with tab2:
            st.subheader("1. 월별 단독 출고 수량 (대)")
            st.dataframe(pivot_monthly.style.format("{:,.0f}"), use_container_width=True)
            
            st.subheader("2. 월별 누적 출고 수량 (대)")
            st.dataframe(pivot_cum.style.format("{:,.0f}"), use_container_width=True)
            
            # CSV 다운로드 기능
            csv = pivot_cum.to_csv().encode('utf-8-sig')
            st.download_button(
                label="📥 누적 출고 데이터 (CSV) 다운로드",
                data=csv,
                file_name="국가별_기기_누적출고현황.csv",
                mime="text/csv"
            )
            
        with tab3:
            st.subheader("상위 15개국 총 출고량 비교")
            fig_bar = px.bar(
                pivot_monthly.head(15).reset_index(),
                x='수출국가', y='총 출고량', color='총 출고량',
                color_continuous_scale='Blues',
                text='총 출고량'
            )
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"파일을 처리하는 중 오류가 발생했습니다: {e}")
else:
    st.info("👆 상단의 [Browse files] 버튼을 눌러 최신 `매출 DB.xlsx` 파일을 업로드해주세요.")
