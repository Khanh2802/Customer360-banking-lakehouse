import streamlit as st
import plotly.express as px
import pandas as pd
from pg_utils import run_pg_query
import mock_data as mock
import theme


def render_ops_health(is_mock=False):
    st.subheader("⚙️ Sức khỏe Pipeline ETL (Ops Pipeline Health)")
    st.write("Theo dõi trạng thái thực thi các DAG Airflow qua bảng vận hành `opslakehouse.flag_job_etl` (đọc trực tiếp từ Postgres, ngoài phạm vi Trino/Lakehouse).")
    st.caption(
        "ℹ️ Trang này kết nối trực tiếp tới Postgres (không qua Trino, vì Trino trong stack "
        "chỉ có catalog `lakehouse`, không có catalog nào trỏ tới bảng vận hành Postgres này)."
    )

    if is_mock:
        df = mock.get_mock_ops_health()
    else:
        try:
            query = """
                SELECT
                    job_name,
                    schema_name,
                    table_name,
                    cob_dt,
                    MAX(CASE WHEN status = 'R' THEN start_time END) AS start_time,
                    MAX(CASE WHEN status = 'S' THEN end_time END) AS end_time,
                    MAX(status) AS latest_status
                FROM opslakehouse.flag_job_etl
                GROUP BY job_name, schema_name, table_name, cob_dt
                ORDER BY cob_dt DESC, start_time
            """
            df = run_pg_query(query)
            if df.empty:
                st.info("ℹ️ Chưa có bản ghi nào trong flag_job_etl.")
                return
            df["start_time"] = pd.to_datetime(df["start_time"])
            df["end_time"] = pd.to_datetime(df["end_time"])
            df["duration_minutes"] = (df["end_time"] - df["start_time"]).dt.total_seconds() / 60.0
        except Exception as e:
            st.error(f"❌ Lỗi khi kết nối trực tiếp tới Postgres: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            df = mock.get_mock_ops_health()

    # Slicer theo cob_dt gần nhất (mặc định)
    available_cob = sorted(df["cob_dt"].astype(str).unique().tolist(), reverse=True)
    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    selected_cob = st.selectbox("📅 Slicer: Ngày xử lý (cob_dt)", options=available_cob, index=0, key="ops_cob_dt")
    st.markdown("</div>", unsafe_allow_html=True)

    df_day = df[df["cob_dt"].astype(str) == selected_cob].copy()

    # 1. KPI Cards
    total_jobs = len(df_day)
    success_jobs = int((df_day["latest_status"] == "S").sum())
    running_jobs = int((df_day["latest_status"] == "R").sum())
    success_rate = (success_jobs / total_jobs * 100.0) if total_jobs else 0.0
    avg_duration = df_day.loc[df_day["latest_status"] == "S", "duration_minutes"].mean()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("📦 Tổng số job (theo bảng)", f"{total_jobs}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("✅ Tỷ lệ thành công", f"{success_rate:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("🔄 Đang chạy / Chưa hoàn tất", f"{running_jobs}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("⏱️ Thời gian chạy TB", f"{avg_duration:.1f} phút" if pd.notna(avg_duration) else "N/A")
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. Gantt-style timeline
    st.write("### 📊 Dòng thời gian thực thi Job (theo cob_dt đã chọn)")
    df_gantt = df_day.dropna(subset=["start_time"]).copy()
    if not df_gantt.empty:
        # Với job đang chạy dở (chưa có end_time), dùng "now" tạm để vẫn vẽ được thanh timeline
        df_gantt["end_time_plot"] = df_gantt["end_time"].fillna(pd.Timestamp.now())
        df_gantt["status_label"] = df_gantt["latest_status"].map({"S": "✅ Success", "R": "🔄 Running"})
        status_colors = {"✅ Success": theme.COLOR_SECONDARY_GREEN, "🔄 Running": theme.COLOR_GOLD}

        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        fig_gantt = px.timeline(
            df_gantt, x_start="start_time", x_end="end_time_plot", y="table_name",
            color="status_label", color_discrete_map=status_colors,
            hover_data=["job_name", "schema_name", "duration_minutes"],
            labels={"table_name": "Bảng đích", "status_label": "Trạng thái"}
        )
        fig_gantt.update_yaxes(autorange="reversed")
        fig_gantt.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=max(300, 28 * len(df_gantt)))
        st.plotly_chart(fig_gantt, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Không có dữ liệu thời gian để vẽ timeline cho cob_dt này.")

    # 3. Bảng chi tiết trạng thái từng job
    st.write("### 📋 Chi tiết trạng thái Job")
    st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
    df_table = df_day.copy()
    df_table["Trạng thái"] = df_table["latest_status"].map({"S": "✅ Success", "R": "🔄 Running"})
    df_table = df_table[["job_name", "schema_name", "table_name", "start_time", "end_time", "duration_minutes", "Trạng thái"]]
    df_table.columns = ["DAG", "Schema", "Bảng đích", "Bắt đầu", "Kết thúc", "Thời lượng (phút)", "Trạng thái"]
    st.dataframe(df_table.sort_values("Bắt đầu"), hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
