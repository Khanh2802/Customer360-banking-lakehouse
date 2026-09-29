import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, get_latest_cob_dt
import mock_data as mock
import theme

# Phí thường niên ước tính (triệu VND/năm) dùng để quy đổi số lượng cơ hội mở thẻ tín
# dụng thành doanh thu phí tiềm năng — CHỈ LÀ GIẢ ĐỊNH MINH HỌA cho mục đích trình bày,
# không phải số liệu chính thức của ngân hàng.
ASSUMED_ANNUAL_FEE_MILLION_VND = 0.5


def render_cross_sell(is_mock=False):
    st.subheader("📊 Cơ hội Bán chéo Sản phẩm (Product Penetration & Cross-sell Opportunity)")
    st.write("Ma trận độ phủ sản phẩm (thẻ tín dụng / tiết kiệm / vay) theo Phân khúc × Nhóm tài sản (AUM), giúp xác định nhóm khách hàng nào còn nhiều dư địa bán chéo nhất.")

    if is_mock:
        df = mock.get_mock_product_penetration()
    else:
        try:
            latest_cob = get_latest_cob_dt()
            query = """
            SELECT
                customer_segment,
                aum_bucket,
                COUNT(*) as total,
                ROUND(AVG(CAST(has_credit_card AS DOUBLE)) * 100.0, 1) as pct_has_credit_card,
                ROUND(AVG(CAST(has_savings AS DOUBLE)) * 100.0, 1) as pct_has_savings,
                ROUND(AVG(CAST(has_loan AS DOUBLE)) * 100.0, 1) as pct_has_loan,
                SUM(CASE WHEN has_credit_card = 0 THEN 1 ELSE 0 END) as opportunity_cc,
                SUM(CASE WHEN has_savings = 0 THEN 1 ELSE 0 END) as opportunity_deposit,
                SUM(CASE WHEN has_loan = 0 THEN 1 ELSE 0 END) as opportunity_loan,
                ROUND(SUM(CASE WHEN has_credit_card = 0 THEN aum_total ELSE 0 END) / 1000000000.0, 1) as cc_opportunity_aum_billion,
                SUM(CASE WHEN has_credit_card = 0 AND txn_count_30d > 0 THEN 1 ELSE 0 END) as cc_opportunity_active_30d
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE cob_dt = CAST(? AS DATE)
            GROUP BY customer_segment, aum_bucket
            ORDER BY total DESC
            """
            df = run_query(query, (latest_cob,))
            if df.empty:
                st.warning("⚠️ Không có dữ liệu.")
                return
            df["estimated_fee_revenue_million_vnd"] = df["opportunity_cc"] * ASSUMED_ANNUAL_FEE_MILLION_VND
        except Exception as e:
            st.error(f"❌ Lỗi khi tải dữ liệu từ Trino: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            df = mock.get_mock_product_penetration()

    # 1. KPI Cards tổng hợp
    total_customers = int(df["total"].sum())
    total_cc_opp = int(df["opportunity_cc"].sum())
    total_deposit_opp = int(df["opportunity_deposit"].sum())
    total_loan_opp = int(df["opportunity_loan"].sum())
    total_est_revenue = float(df["estimated_fee_revenue_million_vnd"].sum())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("💳 Cơ hội mở thẻ tín dụng", f"{total_cc_opp:,} KH")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("💰 Cơ hội mở sổ tiết kiệm", f"{total_deposit_opp:,} KH")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("🏠 Cơ hội vay vốn", f"{total_loan_opp:,} KH")
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric("📈 Doanh thu phí ước tính (thẻ TD)", f"{total_est_revenue:,.0f} Tr. VND/năm")
        st.markdown("</div>", unsafe_allow_html=True)
    st.caption(f"* Doanh thu phí ước tính giả định {ASSUMED_ANNUAL_FEE_MILLION_VND} triệu VND/thẻ/năm — chỉ mang tính minh họa, không phải số liệu chính thức.")

    # 2. Heatmap độ phủ sản phẩm theo Segment x AUM Bucket
    st.write("### 🔥 Ma trận Độ phủ Sản phẩm (% sở hữu) theo Phân khúc × Nhóm tài sản")
    df["segment_aum"] = df["customer_segment"] + " / " + df["aum_bucket"]

    col_heat, col_table = st.columns([3, 2])
    with col_heat:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        df_melt = df.melt(
            id_vars=["segment_aum"],
            value_vars=["pct_has_credit_card", "pct_has_savings", "pct_has_loan"],
            var_name="product", value_name="pct"
        )
        product_labels = {"pct_has_credit_card": "Thẻ tín dụng", "pct_has_savings": "Tiết kiệm", "pct_has_loan": "Vay vốn"}
        df_melt["product"] = df_melt["product"].map(product_labels)
        fig_heat = px.density_heatmap(
            df_melt, x="product", y="segment_aum", z="pct",
            color_continuous_scale=[[0, "#f4a261"], [0.5, theme.COLOR_SECONDARY_GREEN], [1, theme.COLOR_PRIMARY_NAVY]],
            labels={"product": "Sản phẩm", "segment_aum": "Phân khúc / AUM", "pct": "% sở hữu"},
            text_auto=".1f"
        )
        fig_heat.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_heat, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_table:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Ưu tiên bán chéo Thẻ tín dụng (xếp theo AUM cơ hội)</h4>", unsafe_allow_html=True)
        df_priority = df.sort_values("cc_opportunity_aum_billion", ascending=False)[
            ["segment_aum", "opportunity_cc", "cc_opportunity_active_30d", "cc_opportunity_aum_billion"]
        ].copy()
        df_priority.columns = ["Phân khúc/AUM", "SL cơ hội", "Đang hoạt động (30d)", "AUM cơ hội (Tỷ)"]
        st.dataframe(df_priority, hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Bảng chi tiết đầy đủ
    st.write("### 📋 Bảng chi tiết toàn bộ")
    st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
    df_display = df[[
        "customer_segment", "aum_bucket", "total", "pct_has_credit_card", "pct_has_savings",
        "pct_has_loan", "opportunity_cc", "opportunity_deposit", "opportunity_loan"
    ]].copy()
    df_display.columns = [
        "Phân khúc", "AUM Bucket", "Tổng KH", "% Thẻ TD", "% Tiết kiệm", "% Vay",
        "Cơ hội Thẻ TD", "Cơ hội Tiết kiệm", "Cơ hội Vay"
    ]
    st.dataframe(df_display, hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
