import streamlit as st
import duckdb
import pandas as pd
import os

DB_FILE = 'madang.db'

# DB 파일 존재 여부 체크 (없으면 바로 중단)
if not os.path.exists(DB_FILE):
    st.error(f"DB 파일({DB_FILE})을 찾을 수 없습니다. madang.db 위치를 확인하세요.")
    st.stop()

@st.cache_resource
def get_db_connection():
    try:
        conn = duckdb.connect(database=DB_FILE, read_only=False)
        return conn
    except Exception as e:
        st.error(f"데이터베이스 연결 실패: {e}")
        st.stop()

conn = get_db_connection()


# 2. 📖 Streamlit 인터페이스
st.set_page_config(page_title="DuckDB 마당 매니저", layout="wide")
st.title("📚 DuckDB 마당 매니저 (모바일 최적화)")
st.caption("DuckDB 파일로 독립적으로 구동되는 웹 애플리케이션입니다.")

# 3. 📝 이름 입력 기능
st.header("고객 정보 조회")
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
if st.sidebar.checkbox("Orders 테이블 보기"):
    st.sidebar.dataframe(conn.execute("SELECT * FROM Orders").df())

st.divider() # 구분선
st.header("🛒 신규 주문 넣기")

# 1. 입력 폼 생성
with st.form("add_order_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        # 고객 이름 입력
        new_order_name = st.text_input("주문할 고객 이름", placeholder="예: 박지성")
    
    with col2:
        # 책 목록을 DB에서 가져와서 선택 상자로 만들기 (UX 개선)
        # 책 이름은 보이고, 실제로는 bookid를 사용하기 위함
        books_df = conn.execute("SELECT bookid, bookname, price FROM Book").df()
        book_options = {row['bookname']: row['bookid'] for index, row in books_df.iterrows()}
        selected_book_name = st.selectbox("주문할 책 선택", list(book_options.keys()))
    
    # 추가 정보 입력
    col3, col4 = st.columns(2)
    with col3:
        # 판매 가격 (기본값은 책의 정가로 자동 설정)
        default_price = books_df[books_df['bookname'] == selected_book_name]['price'].values[0]
        input_saleprice = st.number_input("판매 가격", value=int(default_price), step=500)
    
    with col4:
        input_date = st.date_input("주문 날짜")

    # 제출 버튼
    submit_btn = st.form_submit_button("주문 등록하기")

# 2. 버튼 클릭 시 데이터 처리 로직
if submit_btn:
    if not new_order_name:
        st.warning("고객 이름을 입력해주세요.")
    else:
        try:
            # A. 이름으로 고객 ID(custid) 찾기
            cust_query = "SELECT custid FROM Customer WHERE name = ?"
            cust_result = conn.execute(cust_query, [new_order_name]).fetchone()
            
            if not cust_result:
                st.error(f"❌ '{new_order_name}' 고객님은 등록되어 있지 않습니다. 먼저 고객 등록이 필요합니다.")
            else:
                cust_id = cust_result[0]
                book_id = book_options[selected_book_name]
                
                # B. 새로운 주문 번호(orderid) 생성 (현재 가장 큰 번호 + 1)
                # 만약 데이터가 하나도 없으면 1번으로 시작
                max_id_query = "SELECT MAX(orderid) FROM Orders"
                max_id_result = conn.execute(max_id_query).fetchone()
                new_order_id = 1 if max_id_result[0] is None else max_id_result[0] + 1
                
                # C. INSERT 실행 (SQL Injection 방지를 위해 파라미터 바인딩 사용)
                insert_query = """
                INSERT INTO Orders (orderid, custid, bookid, saleprice, orderdate)
                VALUES (?, ?, ?, ?, ?)
                """
                conn.execute(insert_query, [new_order_id, cust_id, book_id, input_saleprice, input_date])
                
                st.success(f"✅ 주문 성공! (주문번호: {new_order_id}, 고객: {new_order_name}, 책: {selected_book_name})")
                
                # 데이터 갱신을 위해 2초 뒤 재실행 (선택 사항)
                import time
                time.sleep(1)
                st.rerun()
                
        except Exception as e:
            st.error(f"주문 처리 중 오류 발생: {e}")


# 6. 주문 내역(전체/필터 조회)
st.header("주문 내역")

col1, col2 = st.columns(2)
with col1:
    order_cust_name = st.text_input(
        "주문 내역에서 찾을 고객명(부분 일치 허용)",
        key="order_cust_search"
    )
with col2:
    order_date_range = st.date_input(
        "주문일 범위 선택(옵션)",
        value=[],
        key="order_date_range"
    )

# 기본 주문 조회 쿼리
base_query = """
    SELECT 
        o.orderid   AS 주문번호,
        c.name      AS 고객명,
        b.bookname  AS 서적명,
        o.saleprice AS 판매가,
        o.orderdate AS 주문일
    FROM Orders AS o
    JOIN Customer AS c ON o.custid = c.custid
    JOIN Book     AS b ON o.bookid = b.bookid
"""

conditions = []
params = []

# 1) 고객명 필터 (LIKE)
if order_cust_name:
    conditions.append("c.name LIKE ?")
    params.append(f"%{order_cust_name}%")

# 2) 날짜 범위 필터
if isinstance(order_date_range, list) and len(order_date_range) == 2:
    start, end = order_date_range
    if start and end:
        conditions.append("o.orderdate BETWEEN ? AND ?")
        params.extend([start, end])

# WHERE 절 조합
if conditions:
    base_query += " WHERE " + " AND ".join(conditions)

base_query += " ORDER BY o.orderdate DESC, o.orderid DESC"

# 쿼리 실행 & 표시
df_orders = conn.execute(base_query, params).df()

st.subheader("주문 내역 목록")
st.dataframe(df_orders, use_container_width=True)
st.caption(f"총 {len(df_orders)}건의 주문")




# 페이지 상단에 추가 추천
st.header("📈 실시간 현황")
col1, col2, col3 = st.columns(3)

# 총 주문액 계산
total_sales = conn.execute("SELECT SUM(saleprice) FROM Orders").fetchone()[0]
# 총 주문 건수
total_orders = conn.execute("SELECT COUNT(*) FROM Orders").fetchone()[0]
# 등록된 고객 수
total_customers = conn.execute("SELECT COUNT(*) FROM Customer").fetchone()[0]

col1.metric("총 매출액", f"{total_sales:,.0f}원")
col2.metric("총 주문 건수", f"{total_orders}건")
col3.metric("등록 고객 수", f"{total_customers}명")




