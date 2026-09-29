import streamlit as st
import pandas as pd
import plotly.express as px
from utils import run_query, get_latest_cob_dt
import mock_data as mock
import theme

def render_cohort(is_mock=False):
    st.subheader("📈 Phân tích Cohort & Tỷ lệ Giữ chân Khách hàng (Customer Retention)")
    st.write("Theo dõi sự thay đổi về tỷ lệ hoạt động giao dịch của các nhóm khách hàng dựa trên tháng đăng ký lần đầu.")
    st.caption(
        "ℹ️ Lưu ý: bảng giao dịch nguồn (fact_txn_account/fact_card_txn) hiện chỉ phủ một "
        "khoảng thời gian lịch sử giới hạn (~1 năm gần nhất), trong khi tệp khách hàng "
        "(register_date) trải dài tới 2 năm. Vì vậy, các cohort đăng ký từ giai đoạn đầu có "
        "thể thiếu dữ liệu hoạt động ở những kỳ (period) đầu tiên — đây là giới hạn phủ dữ "
        "liệu, không phải khách hàng thực sự không hoạt động. Truy vấn bên dưới đã tự loại "
        "các mốc `activity_month < cohort_month` để tránh Period Number âm."
    )

    # 1. PowerBI Slicer Bar (Bộ lọc ngang chứa các st.multiselect cuộn xuống được)
    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        selected_segments = st.multiselect(
            "👥 Slicer: Phân khúc Khách hàng",
            options=["VIP", "PRIORITY", "RETAIL"],
            default=["VIP", "PRIORITY", "RETAIL"],
            key="coh_ms_seg"
        )
                    
    with c_s2:
        selected_aum = st.multiselect(
            "💰 Slicer: Nhóm tài sản (AUM Bucket)",
            options=["VIP", "PRIORITY", "AFFLUENT", "MASS"],
            default=["VIP", "PRIORITY", "AFFLUENT", "MASS"],
            key="coh_ms_aum"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if not selected_segments:
        selected_segments = ["VIP", "PRIORITY", "RETAIL"]
    if not selected_aum:
        selected_aum = ["VIP", "PRIORITY", "AFFLUENT", "MASS"]

    # 2. Load Data
    df_cohort = pd.DataFrame()
    if is_mock:
        segment_param = selected_segments[0] if len(selected_segments) == 1 else None
        aum_param = selected_aum[0] if len(selected_aum) == 1 else None
        df_cohort = mock.get_mock_cohort_retention(segment_param, aum_param)
    else:
        try:
            # Lấy COB Date mới nhất (helper dùng chung — xem utils.get_latest_cob_dt)
            latest_cob = get_latest_cob_dt()

            # Dùng placeholder '?' (qmark) thay vì nối chuỗi giá trị trực tiếp vào SQL —
            # tránh SQL injection và tách rõ code khỏi data.
            params = [latest_cob]
            filters = ["m.cob_dt = CAST(? AS DATE)"]

            seg_placeholders = ",".join(["?"] * len(selected_segments))
            filters.append(f"m.customer_segment IN ({seg_placeholders})")
            params.extend(selected_segments)

            aum_placeholders = ",".join(["?"] * len(selected_aum))
            filters.append(f"m.aum_bucket IN ({aum_placeholders})")
            params.extend(selected_aum)

            where_clause = " AND ".join(filters)
            params = tuple(params)
            
            query = f"""
            WITH cohort_base AS (
                SELECT 
                    m.customer_id,
                    DATE_FORMAT(m.register_date, '%Y-%m') AS cohort_month
                FROM lakehouse.sandbox.mart_customer_360_masked m
                WHERE {where_clause}
            ),
            customer_activity AS (
                SELECT DISTINCT
                    t.customer_id,
                    DATE_FORMAT(t.txn_date, '%Y-%m') AS activity_month
                FROM lakehouse.silver.fact_txn_account t
                UNION DISTINCT
                SELECT DISTINCT
                    c.customer_id,
                    DATE_FORMAT(c.txn_date, '%Y-%m') AS activity_month
                FROM lakehouse.silver.fact_card_txn c
            ),
            retention_calc AS (
                SELECT
                    c.cohort_month,
                    a.activity_month,
                    DATE_DIFF('month', 
                              DATE_PARSE(c.cohort_month || '-01', '%Y-%m-%d'), 
                              DATE_PARSE(a.activity_month || '-01', '%Y-%m-%d')
                             ) AS period_num,
                    COUNT(DISTINCT c.customer_id) AS active_customers
                FROM cohort_base c
                JOIN customer_activity a ON c.customer_id = a.customer_id
                WHERE a.activity_month >= c.cohort_month
                GROUP BY 1, 2, 3
            ),
            cohort_sizes AS (
                SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
                FROM cohort_base
                GROUP BY 1
            )
            SELECT
                r.cohort_month,
                s.cohort_size,
                'M' || CAST(r.period_num AS VARCHAR) AS period,
                r.period_num,
                r.active_customers,
                ROUND(CAST(r.active_customers AS DOUBLE) / s.cohort_size * 100.0, 1) AS retention_rate
            FROM retention_calc r
            JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
            WHERE r.period_num <= 11
            ORDER BY r.cohort_month, r.period_num
            """
            
            df_cohort = run_query(query, params)
            
            if df_cohort.empty:
                segment_param = selected_segments[0] if len(selected_segments) == 1 else None
                aum_param = selected_aum[0] if len(selected_aum) == 1 else None
                df_cohort = mock.get_mock_cohort_retention(segment_param, aum_param)
                
        except Exception as e:
            st.error(f"❌ Lỗi khi tải dữ liệu Cohort từ Trino: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            segment_param = selected_segments[0] if len(selected_segments) == 1 else None
            aum_param = selected_aum[0] if len(selected_aum) == 1 else None
            df_cohort = mock.get_mock_cohort_retention(segment_param, aum_param)

    # 3. Render Cohort Heatmap & Analysis
    if not df_cohort.empty:
        if 'period_num' not in df_cohort.columns:
            df_cohort['period_num'] = df_cohort['period'].str.replace('M', '').astype(int)
            
        df_cohort = df_cohort.sort_values(by=['cohort_month', 'period_num'])

        # 3a. Benchmark Retention KPI cards (M1 / M3 / M6 / M9) — trung bình các cohort
        # đang có dữ liệu tại đúng kỳ đó (period_num == mốc), tương tự measure
        # "Month 1/3/6/12 Retention %" đã dựng trên PowerBI.
        st.write("### 🎯 Retention Benchmark theo mốc chuẩn")
        benchmark_periods = [1, 3, 6, 9]
        bench_cols = st.columns(len(benchmark_periods))
        for col, p in zip(bench_cols, benchmark_periods):
            df_p = df_cohort[df_cohort['period_num'] == p]
            with col:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                if not df_p.empty:
                    avg_rate = df_p['retention_rate'].mean()
                    n_cohorts = df_p['cohort_month'].nunique()
                    st.metric(label=f"📌 Retention TB tại M{p}", value=f"{avg_rate:.1f}%")
                    st.caption(f"Trung bình trên {n_cohorts} cohort có dữ liệu tới M{p}")
                else:
                    st.metric(label=f"📌 Retention TB tại M{p}", value="—")
                    st.caption("Chưa có cohort nào đủ dữ liệu tới mốc này")
                st.markdown("</div>", unsafe_allow_html=True)

        # Pivot table
        cohort_pivot = df_cohort.pivot(
            index=['cohort_month', 'cohort_size'], 
            columns='period', 
            values='retention_rate'
        )
        
        col_order = [f"M{i}" for i in range(12) if f"M{i}" in cohort_pivot.columns]
        cohort_pivot = cohort_pivot[col_order]
        
        cohort_pivot_df = cohort_pivot.reset_index()
        cohort_pivot_df.columns = ["Tháng Cohort", "Quy mô"] + col_order
        
        st.write("### 🧮 Ma trận giữ chân Khách hàng (Cohort Retention Matrix)")
        
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("Tabular view of retention rate (%) over subsequent months:")
        
        try:
            styled_df = cohort_pivot_df.style.background_gradient(
                cmap='Greens', 
                subset=col_order, 
                vmin=0, 
                vmax=100
            ).format({col: "{:.1f}%" for col in col_order if col in cohort_pivot_df.columns}, na_rep="-")
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        except Exception:
            st.dataframe(cohort_pivot_df, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 4. Cohort Trends Line Chart
        st.write("### 📈 Xu hướng duy trì của các nhóm Khách hàng")
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        
        top_cohorts = df_cohort[['cohort_month', 'cohort_size']].drop_duplicates().sort_values(by='cohort_size', ascending=False).head(5)['cohort_month'].tolist()
        df_plot = df_cohort[df_cohort['cohort_month'].isin(top_cohorts)].copy()
        
        fig_trend = px.line(
            df_plot,
            x='period',
            y='retention_rate',
            color='cohort_month',
            labels={'period': 'Tháng tiếp theo', 'retention_rate': 'Tỷ lệ hoạt động (%)', 'cohort_month': 'Tháng Cohort'},
            title="Xu hướng tỷ lệ giữ chân của 5 Cohort lớn nhất",
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Dark24
        )
        fig_trend.update_layout(
            yaxis=dict(range=[0, 105]), 
            margin=dict(t=40, b=0, l=0, r=0),
            plot_bgcolor='white'
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Không có dữ liệu Cohort phù hợp.")
