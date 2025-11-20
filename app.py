import streamlit as st
import duckdb
import pandas as pd

# 1. 💾 DB 파일 경로 및 연결 설정
DB_FILE = 'madang.db'

@st.cache_resource # 배포 환경에서 DB 연결을 한 번만 유지하도록 설정
def get_db_connection():
    try:
        conn = duckdb.connect(database=DB_FILE, read_only=False)
        return conn
    except Exception as e:
        # 오류 발생 시 터미널에 출력
        print(f"FATAL ERROR: DB Connection failed - {e}")
        st.error("데이터베이스 연결 실패. 파일을 확인하세요.")
        st.stop()

conn = get_db_connection()

# 2. 📖 Streamlit 인터페이스
st.set_page_config(page_title="DuckDB 마당 매니저", layout="wide")
st.title("📚 DuckDB 마당 매니저 (모바일 최적화)")
st.caption("DuckDB 파일로 독립적으로 구동되는 웹 애플리케이션입니다.")

# 3. 📝 이름 입력 기능
st.header("고객 정보 및 주문 내역 조회")
input_name = st.text_input("조회할 고객 이름을 입력하세요:", value="고객님의 이름") # 👈 기본값을 고객님 이름으로 설정

if st.button("조회 시작") or len(input_name) > 0:
    if len(input_name) > 0:
        # SQL 쿼리: Customer, Book, Orders 테이블 조인하여 이름으로 주문 내역 조회
        query = f"""
        SELECT 
            T1.name AS 고객명, 
            T3.bookname AS 서적명, 
            T2.saleprice AS 판매가, 
            T2.orderdate AS 주문일
        FROM Customer AS T1 
        INNER JOIN Orders AS T2 ON T1.custid = T2.custid
        INNER JOIN Book AS T3 ON T2.bookid = T3.bookid
        WHERE T1.name = '{input_name}';
        """
        
        # 4. 쿼리 실행 및 결과 표시
        try:
            df = conn.execute(query).df()
            
            if df.empty:
                # 주문 내역이 없거나 이름이 Customer 테이블에 없는 경우
                check_customer = conn.execute(f"SELECT * FROM Customer WHERE name = '{input_name}'").df()
                if not check_customer.empty:
                    st.success(f"✅ 고객 '{input_name}'님은 등록되어 있으나, 주문 내역이 없습니다.")
                else:
                    st.warning(f"⚠️ 고객 '{input_name}'님은 데이터베이스에 등록되어 있지 않습니다.")
            else:
                st.subheader(f"'{input_name}'님의 주문 내역")
                st.dataframe(df)

        except Exception as e:
            st.error(f"❌ 쿼리 실행 중 오류가 발생했습니다: {e}")

# 5. 모든 테이블 데이터 확인 (옵션)
st.sidebar.header("전체 데이터 보기")
if st.sidebar.checkbox("Customer 테이블 보기"):
    st.sidebar.dataframe(conn.execute("SELECT * FROM Customer").df())
if st.sidebar.checkbox("Book 테이블 보기"):
    st.sidebar.dataframe(conn.execute("SELECT * FROM Book").df())