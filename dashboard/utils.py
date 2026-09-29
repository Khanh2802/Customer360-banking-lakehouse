import os
import streamlit as st
import pandas as pd
from trino.dbapi import connect

# Ngày cob_dt dùng làm fallback CUỐI CÙNG khi không truy vấn được Trino (mất kết nối,
# bảng rỗng...). Đồng bộ với DATA_COB_DT trong airflow/dags/gold/gold_mart360_dag.py —
# chỉ cần đổi Ở ĐÂY khi re-generate data với cob_dt mới, không cần sửa từng file view.
DEFAULT_COB_DT = os.environ.get("DASHBOARD_DEFAULT_COB_DT", "2025-12-31")

# Timeout (giây) cho mỗi request tới Trino — tránh treo UI quá lâu khi Trino không phản hồi
# trước khi rơi về nhánh fallback (mock data / thông báo lỗi).
TRINO_REQUEST_TIMEOUT = 10

# Caching dữ liệu trong 10 phút để tránh query liên tục khi tương tác UI
@st.cache_data(ttl=600)
def run_query(sql_query: str, params: tuple = ()) -> pd.DataFrame:
    """
    Chạy câu truy vấn SQL trên Trino và trả về Pandas DataFrame.

    params: tuple giá trị tương ứng các dấu '?' (qmark paramstyle của trino-python-client)
    trong sql_query. LUÔN dùng params cho bất kỳ giá trị nào đến từ input người dùng /
    lựa chọn UI thay vì nối trực tiếp vào chuỗi SQL — tránh SQL injection và tách rõ
    code khỏi data. Cache key tự động bao gồm cả params (vì st.cache_data hash theo
    toàn bộ đối số của hàm), nên các bộ lọc khác nhau sẽ có cache riêng, không đụng nhau.
    """
    # Lấy thông số cấu hình từ Environment Variables (hỗ trợ cả chạy local và chạy Docker)
    host = os.environ.get("TRINO_HOST", "localhost")
    port = int(os.environ.get("TRINO_PORT", 8085))
    user = os.environ.get("TRINO_USER", "admin")
    catalog = os.environ.get("TRINO_CATALOG", "lakehouse")
    schema = os.environ.get("TRINO_SCHEMA", "gold")

    conn = None
    try:
        conn = connect(
            host=host,
            port=port,
            user=user,
            catalog=catalog,
            schema=schema,
            request_timeout=TRINO_REQUEST_TIMEOUT,
        )
        cur = conn.cursor()
        cur.execute(sql_query, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=columns)
        return df
    except Exception as e:
        # Cơ chế dự phòng (fallback): nếu đang chạy local mà config trỏ vào trino:8080 (Docker network)
        if host == "trino":
            try:
                conn = connect(
                    host="localhost",
                    port=8085,
                    user=user,
                    catalog=catalog,
                    schema=schema,
                    request_timeout=TRINO_REQUEST_TIMEOUT,
                )
                cur = conn.cursor()
                cur.execute(sql_query, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                df = pd.DataFrame(rows, columns=columns)
                return df
            except Exception as inner_e:
                raise Exception(f"Không thể kết nối đến Trino (cả 'trino:8080' và 'localhost:8085'): {inner_e}")
        raise Exception(f"Không thể kết nối đến Trino tại {host}:{port}: {e}")
    finally:
        if conn:
            conn.close()

def clear_query_cache():
    """Xóa cache dữ liệu để ép buộc query lại từ Trino."""
    st.cache_data.clear()

def get_latest_cob_dt() -> str:
    """
    Trả về cob_dt (dạng 'YYYY-MM-DD') mới nhất hiện có trong mart_customer_360_masked.

    Dùng chung cho mọi trang (overview/campaign/customer_profile/cohort) thay vì mỗi
    view tự query + tự hard-code fallback riêng — tránh lệch giá trị giữa các file khi
    dữ liệu được re-generate với cob_dt khác.
    """
    try:
        df = run_query("SELECT MAX(cob_dt) as max_cob FROM lakehouse.sandbox.mart_customer_360_masked")
        if not df.empty and pd.notna(df["max_cob"].iloc[0]):
            return str(df["max_cob"].iloc[0])
    except Exception:
        pass
    return DEFAULT_COB_DT
