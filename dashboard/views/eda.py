import streamlit as st
import plotly.express as px
import pandas as pd
from utils import run_query, get_latest_cob_dt
import mock_data as mock
import theme


def render_eda(is_mock=False):
    st.subheader("🧬 Phân tích Khám phá Dữ liệu (EDA) & Nhân khẩu học Khách hàng")
    st.write("Bức tranh tổng thể về cấu trúc tệp khách hàng: giới tính, độ tuổi, chi nhánh, trạng thái KYC và xu hướng đăng ký theo thời gian.")

    # 1. PowerBI Slicer Bar
    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        selected_segments = st.multiselect(
            "👥 Slicer: Phân khúc Khách hàng",
            options=["VIP", "PRIORITY", "RETAIL"],
            default=["VIP", "PRIORITY", "RETAIL"],
            key="eda_ms_seg"
        )
    with c_s2:
        selected_gender = st.multiselect(
            "🚻 Slicer: Giới tính",
            options=["M", "F"],
            default=["M", "F"],
            key="eda_ms_gender"
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if not selected_segments:
        selected_segments = ["VIP", "PRIORITY", "RETAIL"]
    if not selected_gender:
        selected_gender = ["M", "F"]

    # 2. Load & Filter Data
    if is_mock:
        kpis = mock.get_mock_eda_kpis()
        df_gender = mock.get_mock_gender_distribution()
        df_age = mock.get_mock_age_distribution()
        df_branch = mock.get_mock_branch_distribution()
        df_kyc = mock.get_mock_kyc_distribution()
        df_trend = mock.get_mock_register_trend()
    else:
        try:
            params = []
            seg_placeholders = ",".join(["?"] * len(selected_segments))
            gender_placeholders = ",".join(["?"] * len(selected_gender))
            where_str = f"customer_segment IN ({seg_placeholders}) AND gender IN ({gender_placeholders})"
            params.extend(selected_segments)
            params.extend(selected_gender)
            params = tuple(params)

            # KPIs
            kpi_query = f"""
            SELECT
                COUNT(*) as total_customers,
                ROUND(AVG(age), 1) as avg_age,
                ROUND(CAST(SUM(CASE WHEN kyc_status = 'VERIFIED' THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(*) * 100.0, 1) as pct_kyc_verified,
                ROUND(CAST(SUM(CASE WHEN DATE_FORMAT(register_date, '%Y-%m') = DATE_FORMAT(CURRENT_DATE, '%Y-%m') THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(*) * 100.0, 2) as pct_new_this_month
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_str}
            """
            df_kpis = run_query(kpi_query, params)
            if df_kpis.empty or df_kpis["total_customers"].iloc[0] == 0:
                st.warning("⚠️ Không có dữ liệu khách hàng thỏa mãn bộ lọc hiện tại.")
                return
            kpis = {
                "total_customers": int(df_kpis["total_customers"].iloc[0]),
                "avg_age": float(df_kpis["avg_age"].iloc[0]) if df_kpis["avg_age"].iloc[0] is not None else 0.0,
                "pct_kyc_verified": float(df_kpis["pct_kyc_verified"].iloc[0]) if df_kpis["pct_kyc_verified"].iloc[0] is not None else 0.0,
                "pct_new_this_month": float(df_kpis["pct_new_this_month"].iloc[0]) if df_kpis["pct_new_this_month"].iloc[0] is not None else 0.0,
            }

            # Gender
            df_gender = run_query(f"""
                SELECT gender, COUNT(*) as customer_count
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY gender
            """, params)

            # Age bucket
            df_age = run_query(f"""
                SELECT
                    CASE
                        WHEN age < 25 THEN '<25'
                        WHEN age BETWEEN 25 AND 34 THEN '25-34'
                        WHEN age BETWEEN 35 AND 44 THEN '35-44'
                        WHEN age BETWEEN 45 AND 54 THEN '45-54'
                        WHEN age BETWEEN 55 AND 64 THEN '55-64'
                        ELSE '65+'
                    END as age_bucket,
                    COUNT(*) as customer_count
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY 1
            """, params)

            # Branch distribution
            df_branch = run_query(f"""
                SELECT primary_branch_code, COUNT(*) as customer_count
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY primary_branch_code
                ORDER BY customer_count DESC
                LIMIT 15
            """, params)

            # KYC status
            df_kyc = run_query(f"""
                SELECT kyc_status, COUNT(*) as customer_count
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY kyc_status
            """, params)

            # Register date trend (proxy cho "thời gian tạo thẻ")
            df_trend = run_query(f"""
                SELECT DATE_FORMAT(register_date, '%Y-%m') as reg_month, COUNT(*) as customer_count
                FROM lakehouse.sandbox.mart_customer_360_masked
                WHERE {where_str}
                GROUP BY 1
                ORDER BY 1
            """, params)

        except Exception as e:
            st.error(f"❌ Lỗi khi tải dữ liệu từ Trino: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            kpis = mock.get_mock_eda_kpis()
            df_gender = mock.get_mock_gender_distribution()
            df_age = mock.get_mock_age_distribution()
            df_branch = mock.get_mock_branch_distribution()
            df_kyc = mock.get_mock_kyc_distribution()
            df_trend = mock.get_mock_register_trend()

    # 3. KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="👥 Tổng khách hàng", value=f"{kpis['total_customers']:,}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="🎂 Tuổi trung bình", value=f"{kpis['avg_age']:.1f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="✅ Tỷ lệ KYC đã xác thực", value=f"{kpis['pct_kyc_verified']:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="🆕 % KH đăng ký trong tháng hiện tại", value=f"{kpis['pct_new_this_month']:.2f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    # 4. Gender + Age
    col_gender, col_age = st.columns(2)
    with col_gender:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Phân bổ theo Giới tính</h4>", unsafe_allow_html=True)
        gender_colors = {"M": theme.COLOR_PRIMARY_NAVY, "F": theme.COLOR_GOLD}
        fig_gender = px.pie(
            df_gender, values="customer_count", names="gender", hole=0.5,
            color="gender", color_discrete_map=gender_colors
        )
        fig_gender.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_gender, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_age:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Phân bổ theo Nhóm tuổi</h4>", unsafe_allow_html=True)
        age_order = ["<25", "25-34", "35-44", "45-54", "55-64", "65+"]
        df_age["age_bucket"] = pd.Categorical(df_age["age_bucket"], categories=age_order, ordered=True)
        df_age = df_age.sort_values("age_bucket")
        fig_age = px.bar(
            df_age, x="age_bucket", y="customer_count", text_auto=".2s",
            labels={"age_bucket": "Nhóm tuổi", "customer_count": "Số lượng khách hàng"},
            color_discrete_sequence=[theme.COLOR_SECONDARY_GREEN]
        )
        fig_age.update_layout(margin=dict(t=10, b=0, l=0, r=0), plot_bgcolor="white")
        st.plotly_chart(fig_age, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. KYC status + Branch distribution
    col_kyc, col_branch = st.columns([1, 2])
    with col_kyc:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Trạng thái KYC</h4>", unsafe_allow_html=True)
        kyc_colors = {"VERIFIED": theme.COLOR_SECONDARY_GREEN, "PENDING": theme.COLOR_GOLD}
        fig_kyc = px.pie(
            df_kyc, values="customer_count", names="kyc_status", hole=0.5,
            color="kyc_status", color_discrete_map=kyc_colors
        )
        fig_kyc.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_kyc, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_branch:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Top 15 Chi nhánh theo Số lượng khách hàng</h4>", unsafe_allow_html=True)
        fig_branch = px.bar(
            df_branch.sort_values("customer_count"), y="primary_branch_code", x="customer_count",
            orientation="h", text_auto=".2s",
            labels={"primary_branch_code": "Mã chi nhánh", "customer_count": "Số lượng khách hàng"},
            color_discrete_sequence=[theme.COLOR_PRIMARY_NAVY]
        )
        fig_branch.update_layout(margin=dict(t=10, b=0, l=0, r=0), plot_bgcolor="white")
        st.plotly_chart(fig_branch, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 6. Register date trend (proxy cho thời gian tạo thẻ/mở tài khoản)
    st.write("### 📅 Xu hướng Đăng ký Khách hàng theo Thời gian")
    st.caption(
        "⚠️ Lưu ý: dữ liệu masked hiện có không chứa trường ngày phát hành thẻ riêng biệt. "
        "Biểu đồ dưới đây dùng **register_date** (ngày đăng ký/mở hồ sơ khách hàng) làm đại diện "
        "(proxy) hợp lý nhất cho \"thời gian tạo thẻ\", vì đây là thời điểm khách hàng chính thức "
        "gia nhập hệ thống ngân hàng."
    )
    st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
    fig_trend = px.line(
        df_trend, x="reg_month", y="customer_count", markers=True,
        labels={"reg_month": "Tháng đăng ký", "customer_count": "Số lượng khách hàng mới"},
        color_discrete_sequence=[theme.COLOR_SECONDARY_GREEN]
    )
    fig_trend.update_layout(margin=dict(t=10, b=0, l=0, r=0), plot_bgcolor="white")
    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
