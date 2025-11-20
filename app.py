import streamlit as st
import duckdb
import pandas as pd
import os

DB_FILE = 'madang.db'

# 1. 설정 및 DB 연결
st.set_page_config(page_title="DuckDB 마당 매니저", layout="wide")

@st.cache_resource
def get_db_connection():
    conn = duckdb.connect(database=DB_FILE, read_only=False)
    return conn

try:
    conn = get_db_connection()
except Exception as e:
    st.error(f"DB 연결 오류: {e}")
    st.stop()

st.title("📚 DuckDB 마당 매니저")

# 2. 대시보드 (통계)
st.markdown("### 📈 실시간 현황")
try:
    # 간단한 통계 쿼리 (NULL 처리 포함)
    stats = conn.execute("""
        SELECT 
            COALESCE(SUM(saleprice), 0) as total_sales,
            COUNT(*) as total_orders
        FROM Orders
    """).fetchone()
    
    col1, col2 = st.columns(2)
    col1.metric("총 매출액", f"{stats[0]:,.0f}원")
    col2.metric("누적 주문수", f"{stats[1]}건")
except Exception as e:
    st.warning("아직 주문 데이터가 없습니다.")

st.divider()

# 3. 검색 기능 (Form 사용 및 파라미터 바인딩 적용)
st.markdown("### 🔍 고객 주문 조회")

with st.form("search_form"):
    col_input, col_btn = st.columns([4, 1])
    input_name = col_input.text_input("고객 이름", placeholder="예: 박지성")
    submitted = col_btn.form_submit_button("조회하기")

if submitted and input_name:
    # 파라미터 바인딩 (?) 사용으로 보안 강화
    query = """
    SELECT 
        T1.name AS 고객명, 
        T3.bookname AS 서적명, 
        T2.saleprice AS 판매가, 
        T2.orderdate AS 주문일
    FROM Customer AS T1 
    JOIN Orders AS T2 ON T1.custid = T2.custid
    JOIN Book AS T3 ON T2.bookid = T3.bookid
    WHERE T1.name = ?
    """
    df = conn.execute(query, [input_name]).df()
    
    if not df.empty:
        st.success(f"✅ '{input_name}'님의 주문 내역을 찾았습니다.")
        st.dataframe(df, use_container_width=True)
    else:
        # 고객 존재 여부 확인 (파라미터 바인딩)
        check = conn.execute("SELECT 1 FROM Customer WHERE name = ?", [input_name]).fetchone()
        if check:
            st.info(f"ℹ️ '{input_name}' 고객님은 등록되어 있지만, 주문 내역이 없습니다.")
        else:
            st.error(f"❌ '{input_name}' 고객님을 찾을 수 없습니다.")
