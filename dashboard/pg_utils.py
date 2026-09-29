"""
Kết nối trực tiếp tới PostgreSQL (KHÔNG qua Trino) — chỉ dùng cho Trang "Sức khỏe Pipeline
ETL" (Ops Health), để đọc bảng vận hành opslakehouse.flag_job_etl.

Lý do không dùng utils.run_query() (Trino) như các trang khác: Trino trong stack này chỉ
có DUY NHẤT một catalog `lakehouse` (Iceberg REST) — không có catalog nào trỏ tới Postgres.
Bảng flag_job_etl là bảng vận hành nội bộ của Airflow/Postgres, không thuộc Lakehouse
(bronze/silver/gold), nên việc đọc trực tiếp qua psycopg2 ở đây không vi phạm quy tắc
"không đụng production Lakehouse" (Trang 1-4 vẫn chỉ đọc qua Trino/sandbox như cũ).

Container `postgres` map cổng 5432:5432 ra host, nên Streamlit (chạy trên máy host) có thể
kết nối thẳng qua localhost:5432 giống cách utils.py mặc định TRINO_HOST=localhost.
"""

import os
import pandas as pd
import streamlit as st

try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


@st.cache_data(ttl=120)
def run_pg_query(sql_query: str, params: tuple = None) -> pd.DataFrame:
    """
    Chạy câu truy vấn SQL trên Postgres (opslakehouse schema) và trả về Pandas DataFrame.
    Cache 2 phút (ngắn hơn Trino vì đây là dữ liệu vận hành thay đổi liên tục trong ngày).
    """
    if not _PSYCOPG2_AVAILABLE:
        raise ImportError(
            "Thiếu thư viện psycopg2-binary. Cài đặt bằng: pip install psycopg2-binary "
            "(đã có sẵn trong dashboard/requirements.txt, chạy `pip install -r requirements.txt`)."
        )

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("POSTGRES_PORT", 5432))
    user = os.environ.get("POSTGRES_USER", "card_crm")
    password = os.environ.get("POSTGRES_PASSWORD", "Cardcrm123")
    dbname = os.environ.get("POSTGRES_DB", "card_crm")

    conn = None
    try:
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password,
            dbname=dbname, connect_timeout=8,
        )
        df = pd.read_sql_query(sql_query, conn, params=params)
        return df
    except Exception as e:
        # Fallback: nếu đang chạy config trỏ vào hostname Docker network 'postgres' mà
        # thất bại (thường do chạy Streamlit ngoài Docker, trên host), thử lại qua localhost.
        if host == "postgres":
            try:
                conn2 = psycopg2.connect(
                    host="localhost", port=5432, user=user, password=password,
                    dbname=dbname, connect_timeout=8,
                )
                df = pd.read_sql_query(sql_query, conn2, params=params)
                conn2.close()
                return df
            except Exception as inner_e:
                raise Exception(f"Không thể kết nối Postgres (cả 'postgres' và 'localhost'): {inner_e}")
        raise Exception(f"Không thể kết nối Postgres tại {host}:{port}: {e}")
    finally:
        if conn:
            conn.close()


def clear_pg_cache():
    """Xóa cache dữ liệu Postgres để ép buộc query lại."""
    run_pg_query.clear()
