import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import run_query, DEFAULT_COB_DT
import mock_data as mock
import geo_utils
import theme


def render_rfm_geo(is_mock=False):
    st.subheader("🎖️ Phân tích Hành vi Khách hàng (RFM) & Phân bố Địa lý")
    st.write("Chất lượng tệp khách hàng theo phân khúc RFM, cơ cấu tài sản, kênh giao dịch, và phân bố khách hàng/AUM trên bản đồ Việt Nam.")

    # 1. Slicer
    available_months = [DEFAULT_COB_DT[:7]]
    months_query_failed = False
    if not is_mock:
        try:
            df_dates = run_query("SELECT DISTINCT cob_dt FROM lakehouse.sandbox.mart_customer_360_masked ORDER BY cob_dt DESC")
            if not df_dates.empty:
                df_dates["month_str"] = pd.to_datetime(df_dates["cob_dt"]).dt.strftime("%Y-%m")
                available_months = sorted(df_dates["month_str"].unique().tolist(), reverse=True)
        except Exception:
            months_query_failed = True

    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    c_s1, c_s2, c_s3 = st.columns(3)
    with c_s1:
        selected_months = st.multiselect(
            "📅 Slicer: Tháng báo cáo", options=available_months,
            default=[available_months[0]], key="rg_ms_month"
        )
    with c_s2:
        selected_segments = st.multiselect(
            "👥 Slicer: Phân khúc Khách hàng", options=["VIP", "PRIORITY", "RETAIL"],
            default=["VIP", "PRIORITY", "RETAIL"], key="rg_ms_seg"
        )
    with c_s3:
        selected_products = st.multiselect(
            "💳 Slicer: Sản phẩm sở hữu", options=["CASA", "Savings", "Loan", "Credit Card"],
            default=["CASA", "Savings", "Loan", "Credit Card"], key="rg_ms_prod"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if months_query_failed:
        st.caption(f"⚠️ Không lấy được danh sách tháng báo cáo từ Trino — đang dùng giá trị mặc định ({available_months[0]}).")

    if not selected_months:
        selected_months = [available_months[0]]
    if not selected_segments:
        selected_segments = ["VIP", "PRIORITY", "RETAIL"]
    if not selected_products:
        selected_products = ["CASA", "Savings", "Loan", "Credit Card"]

    # 2. Load Data
    if is_mock:
        df_rfm = mock.get_mock_rfm_distribution()
        df_aum = mock.get_mock_aum_distribution()
        df_channel = mock.get_mock_channel_distribution()
        df_geo_city = mock.get_mock_geo_city_distribution()
    else:
        try:
            where_clauses = []
            params = []

            month_placeholders = ",".join(["?"] * len(selected_months))
            where_clauses.append(f"DATE_FORMAT(cob_dt, '%Y-%m') IN ({month_placeholders})")
            params.extend(selected_months)

            seg_placeholders = ",".join(["?"] * len(selected_segments))
            where_clauses.append(f"customer_segment IN ({seg_placeholders})")
            params.extend(selected_segments)

            prod_conditions = []
            if "CASA" in selected_products:
                prod_conditions.append("total_accounts > 0")
            if "Savings" in selected_products:
                prod_conditions.append("has_savings = 1")
            if "Loan" in selected_products:
                prod_conditions.append("has_loan = 1")
            if "Credit Card" in selected_products:
                prod_conditions.append("has_credit_card = 1")
            where_clauses.append("(" + " OR ".join(prod_conditions) + ")" if prod_conditions else "1 = 0")

            where_str = " AND ".join(where_clauses)
            params = tuple(params)

            df_rfm = run_query(f"""
                SELECT rfm_segment, COUNT(*) as customer_count,
                    ROUND(SUM(aum_total) / 1000000000.0, 2) as total_aum_billion,
                    ROUND(AVG(aum_total) / 1000000.0, 2) as avg_aum_million,
                    ROUND(AVG(txn_count_30d), 1) as avg_txn_30d,
                    ROUND(AVG(txn_amount_30d) / 1000000.0, 2) as avg_txn_amt_30d_million,
                    COUNT(CASE WHEN has_credit_card = 0 THEN 1 END) as no_credit_card_cnt,
                    COUNT(CASE WHEN churn_flag = 1 THEN 1 END) as churn_flag_cnt
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY rfm_segment
            """, params)

            df_aum = run_query(f"""
                SELECT aum_bucket, COUNT(*) as customer_count,
                    ROUND(SUM(aum_total) / 1000000000.0, 2) as total_aum_billion
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY aum_bucket
            """, params)

            df_channel = run_query(f"""
                SELECT primary_channel, COUNT(*) as customer_count
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY primary_channel
            """, params)

            # Bản đồ dùng THẲNG cột city thật (dim_customer_masked.city) thay vì suy
            # diễn qua branch_code. mart_customer_360_masked không có cột city nên
            # phải JOIN sang dim_customer_masked (bản ghi is_current=1) để lấy nó —
            # dùng alias m./d. riêng cho join này để tránh đụng where_str dùng chung
            # ở trên (2 bảng đều có cột customer_segment nên cần prefix rõ ràng).
            geo_where_clauses = []
            geo_params = []
            geo_where_clauses.append(f"DATE_FORMAT(m.cob_dt, '%Y-%m') IN ({month_placeholders})")
            geo_params.extend(selected_months)
            geo_where_clauses.append(f"m.customer_segment IN ({seg_placeholders})")
            geo_params.extend(selected_segments)
            geo_prod_conditions = []
            if "CASA" in selected_products:
                geo_prod_conditions.append("m.total_accounts > 0")
            if "Savings" in selected_products:
                geo_prod_conditions.append("m.has_savings = 1")
            if "Loan" in selected_products:
                geo_prod_conditions.append("m.has_loan = 1")
            if "Credit Card" in selected_products:
                geo_prod_conditions.append("m.has_credit_card = 1")
            geo_where_clauses.append("(" + " OR ".join(geo_prod_conditions) + ")" if geo_prod_conditions else "1 = 0")
            geo_where_str = " AND ".join(geo_where_clauses)
            geo_params = tuple(geo_params)

            df_geo_city = run_query(f"""
                SELECT
                    d.city,
                    COUNT(DISTINCT m.customer_id) as customer_count,
                    ROUND(SUM(m.aum_total) / 1000000000.0, 2) as total_aum_billion
                FROM lakehouse.sandbox.mart_customer_360_masked m
                JOIN lakehouse.sandbox.dim_customer_masked d
                    ON m.customer_id = d.customer_id AND d.is_current = 1
                WHERE {geo_where_str}
                GROUP BY d.city
            """, geo_params)

            if df_rfm.empty:
                st.warning("⚠️ Không có dữ liệu khách hàng thỏa mãn bộ lọc hiện tại.")
                return

        except Exception as e:
            st.error(f"❌ Lỗi khi tải dữ liệu từ Trino: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            df_rfm = mock.get_mock_rfm_distribution()
            df_aum = mock.get_mock_aum_distribution()
            df_channel = mock.get_mock_channel_distribution()
            df_geo_city = mock.get_mock_geo_city_distribution()

    # 3. RFM Segment chart + table
    st.write("### 🎖️ Phân tích hành vi Khách giữ chân (RFM)")
    # 7 nhóm RFM CHUẨN thực tế theo code_etl/gold/segmentation/rfm_segment.yml,
    # xếp từ tốt nhất -> kém nhất theo rfm_score.
    rfm_order = [
        "Champions", "Loyal Customers", "Potential Loyalists", "New Customers",
        "At Risk", "Hibernating", "Lost"
    ]
    df_rfm["rfm_segment"] = pd.Categorical(df_rfm["rfm_segment"], categories=rfm_order, ordered=True)
    df_rfm = df_rfm.sort_values("rfm_segment").dropna(subset=["rfm_segment"])

    rfm_colors_map = {
        "Champions": theme.COLOR_GOLD, "Loyal Customers": theme.COLOR_SECONDARY_GREEN,
        "Potential Loyalists": "#3a5a40", "New Customers": "#a3b18a",
        "At Risk": "#e63946", "Hibernating": "#6c757d", "Lost": "#343a40"
    }

    col_chart, col_table = st.columns([3, 2])
    with col_chart:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Số lượng khách hàng theo phân khúc RFM</h4>", unsafe_allow_html=True)
        fig_rfm = px.bar(
            df_rfm, x="rfm_segment", y="customer_count", text_auto=".3s",
            labels={"rfm_segment": "Phân khúc RFM", "customer_count": "Số lượng khách hàng"},
            color="rfm_segment", color_discrete_map=rfm_colors_map
        )
        fig_rfm.update_layout(showlegend=False, margin=dict(t=10, b=0, l=0, r=0), plot_bgcolor="white")
        st.plotly_chart(fig_rfm, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_table:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Bảng chi tiết phân khúc RFM</h4>", unsafe_allow_html=True)
        df_rfm_display = df_rfm[["rfm_segment", "customer_count", "total_aum_billion", "avg_txn_30d", "churn_flag_cnt"]].copy()
        df_rfm_display.columns = ["Phân khúc", "Khách hàng", "Tổng AUM (Tỷ)", "Giao dịch TB (30d)", "Số khách Churn"]
        st.dataframe(df_rfm_display, hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 4. AUM + Channel
    col_aum, col_chan = st.columns(2)
    aum_colors_map = {"VIP": theme.COLOR_GOLD, "PRIORITY": theme.COLOR_SECONDARY_GREEN, "AFFLUENT": theme.COLOR_PRIMARY_NAVY, "MASS": "#a3b18a"}
    with col_aum:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Phân bổ Tổng AUM (Tỷ VND) theo nhóm tài sản</h4>", unsafe_allow_html=True)
        fig_aum = px.pie(df_aum, values="total_aum_billion", names="aum_bucket", hole=0.4, color="aum_bucket", color_discrete_map=aum_colors_map)
        fig_aum.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_aum, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_chan:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Phân bổ theo Kênh giao dịch chính (30 ngày)</h4>", unsafe_allow_html=True)
        channel_colors = [theme.COLOR_PRIMARY_NAVY, theme.COLOR_SECONDARY_GREEN, theme.COLOR_GOLD, "#5c677d", "#abc4ff"]
        fig_chan = px.pie(df_channel, values="customer_count", names="primary_channel", hole=0.4, color_discrete_sequence=channel_colors)
        fig_chan.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_chan, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. Vietnam Map — bản đồ bong bóng theo THÀNH PHỐ THẬT (cột city gốc,
    # KHÔNG còn suy diễn qua branch_code prefix nữa).
    st.write("### 🗺️ Phân bố Khách hàng & Tài sản trên Bản đồ Việt Nam")
    st.caption(
        "ℹ️ Bản đồ dùng thẳng cột `city` gốc (dim_customer_masked.city) theo đúng dữ liệu "
        "thật, không suy diễn qua branch_code. Lưu ý: cột `city` trong bộ dữ liệu hiện tại "
        "chỉ được sinh với đúng 3 giá trị cố định (Hà Nội / TP.HCM / Đà Nẵng, xem "
        "data_generator/sql_generators/oracle_gen.sql) nên bản đồ chỉ có tối đa 3 điểm — "
        "thô hơn so với cách suy diễn theo branch_code (~12+ tỉnh) nhưng phản ánh đúng field "
        "gốc như yêu cầu."
    )
    df_province = geo_utils.aggregate_by_city(df_geo_city, city_col="city")

    if not df_province.empty:
        col_map, col_rank = st.columns([2, 1])
        with col_map:
            st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
            fig_map = go.Figure()
            fig_map.add_trace(go.Scattergeo(
                lon=df_province["lon"], lat=df_province["lat"],
                text=df_province["province_name"] + "<br>Khách hàng: " + df_province["customer_count"].astype(str)
                     + "<br>AUM: " + df_province["total_aum_billion"].round(1).astype(str) + " tỷ VND",
                hoverinfo="text",
                mode="markers",
                marker=dict(
                    size=df_province["customer_count"],
                    sizemode="area",
                    sizeref=2.0 * df_province["customer_count"].max() / (40.0 ** 2),
                    sizemin=6,
                    color=df_province["total_aum_billion"],
                    colorscale=[[0, theme.COLOR_PRIMARY_NAVY], [0.5, theme.COLOR_SECONDARY_GREEN], [1, theme.COLOR_GOLD]],
                    colorbar=dict(title="AUM (Tỷ VND)"),
                    line=dict(width=1, color="white"),
                )
            ))
            fig_map.update_geos(
                scope="asia",
                center=dict(lon=106, lat=16),
                projection_scale=6,
                showland=True, landcolor="#EBEDE3",
                showcountries=True, countrycolor="white",
                showcoastlines=True, coastlinecolor="white",
                lataxis_range=[7, 24], lonaxis_range=[100, 112],
            )
            fig_map.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=520)
            st.plotly_chart(fig_map, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_rank:
            st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
            st.markdown("<h4>Xếp hạng Thành phố theo AUM</h4>", unsafe_allow_html=True)
            df_rank = df_province.sort_values("total_aum_billion", ascending=False)[["province_name", "customer_count", "total_aum_billion"]]
            df_rank.columns = ["Thành phố", "Khách hàng", "AUM (Tỷ VND)"]
            st.dataframe(df_rank, hide_index=True, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Không có dữ liệu city phù hợp để vẽ bản đồ.")
