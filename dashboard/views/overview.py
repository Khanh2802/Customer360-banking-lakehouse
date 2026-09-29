import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils import run_query, DEFAULT_COB_DT
import mock_data as mock
import theme

def render_overview(is_mock=False):
    # Lấy danh sách tháng khả dụng (Month Slicer).
    # Fallback chỉ là tháng của DEFAULT_COB_DT (KHÔNG phải danh sách tháng có thật) —
    # chỉ dùng khi không query được Trino; xem cảnh báo bên dưới nếu rơi vào trường hợp này.
    available_months = [DEFAULT_COB_DT[:7]]
    months_query_failed = False
    if not is_mock:
        try:
            df_dates = run_query("SELECT DISTINCT cob_dt FROM lakehouse.sandbox.mart_customer_360_masked ORDER BY cob_dt DESC")
            if not df_dates.empty:
                df_dates['month_str'] = pd.to_datetime(df_dates['cob_dt']).dt.strftime('%Y-%m')
                available_months = sorted(df_dates['month_str'].unique().tolist(), reverse=True)
        except Exception:
            months_query_failed = True

    # 1. PowerBI Slicer Bar (Bộ lọc ngang chứa các st.multiselect cuộn xuống được)
    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    c_s1, c_s2, c_s3 = st.columns(3)
    
    with c_s1:
        selected_months = st.multiselect(
            "📅 Slicer: Tháng báo cáo",
            options=available_months,
            default=[available_months[0]],
            key="ov_ms_month"
        )
                
    with c_s2:
        selected_segments = st.multiselect(
            "👥 Slicer: Phân khúc Khách hàng",
            options=["VIP", "PRIORITY", "RETAIL"],
            default=["VIP", "PRIORITY", "RETAIL"],
            key="ov_ms_seg"
        )
                    
    with c_s3:
        selected_products = st.multiselect(
            "💳 Slicer: Sản phẩm sở hữu",
            options=["CASA", "Savings", "Loan", "Credit Card"],
            default=["CASA", "Savings", "Loan", "Credit Card"],
            key="ov_ms_prod"
        )
                    
    st.markdown("</div>", unsafe_allow_html=True)

    if months_query_failed:
        st.caption(f"⚠️ Không lấy được danh sách tháng báo cáo từ Trino — đang dùng giá trị mặc định ({available_months[0]}).")

    # 2. Xây dựng bộ lọc SQL động hoặc Giả lập
    if not selected_months:
        selected_months = [available_months[0]]
    if not selected_segments:
        selected_segments = ["VIP", "PRIORITY", "RETAIL"]
    if not selected_products:
        selected_products = ["CASA", "Savings", "Loan", "Credit Card"]

    # 3. Load & Filter Data
    if is_mock:
        # Load and filter mock data
        kpis = mock.get_mock_overview_kpis()
        df_rfm = mock.get_mock_rfm_distribution()
        df_aum = mock.get_mock_aum_distribution()
        df_channel = mock.get_mock_channel_distribution()
        df_branch = mock.get_mock_branch_distribution()
        
        # Áp dụng bộ lọc giả lập lên mock data
        scale_factor = len(selected_segments) / 3.0 * (len(selected_months) / 1.0)
        kpis["total_customers"] = int(kpis["total_customers"] * scale_factor)
        kpis["total_aum"] = kpis["total_aum"] * scale_factor
        df_rfm = df_rfm.copy()
        df_rfm["customer_count"] = (df_rfm["customer_count"] * scale_factor).astype(int)
    else:
        try:
            # Tạo điều kiện lọc SQL — dùng placeholder '?' (qmark), KHÔNG nối chuỗi giá trị
            # trực tiếp vào SQL, để tránh SQL injection và tách rõ code khỏi data.
            where_clauses = []
            params = []

            # Lọc theo tháng
            month_placeholders = ",".join(["?"] * len(selected_months))
            where_clauses.append(f"DATE_FORMAT(cob_dt, '%Y-%m') IN ({month_placeholders})")
            params.extend(selected_months)

            # Lọc theo Phân khúc
            seg_placeholders = ",".join(["?"] * len(selected_segments))
            where_clauses.append(f"customer_segment IN ({seg_placeholders})")
            params.extend(selected_segments)

            # Lọc theo Sản phẩm sở hữu (các fragment này cố định/whitelist, không phải giá
            # trị người dùng nhập, nên không cần tham số hóa)
            prod_conditions = []
            if "CASA" in selected_products:
                prod_conditions.append("total_accounts > 0")
            if "Savings" in selected_products:
                prod_conditions.append("has_savings = 1")
            if "Loan" in selected_products:
                prod_conditions.append("has_loan = 1")
            if "Credit Card" in selected_products:
                prod_conditions.append("has_credit_card = 1")
                
            if prod_conditions:
                where_clauses.append("(" + " OR ".join(prod_conditions) + ")")
            else:
                where_clauses.append("1 = 0")
                
            where_str = " AND ".join(where_clauses)
            params = tuple(params)
            
            # Query KPIs
            kpi_query = f"""
            SELECT 
                COUNT(*) as total_customers,
                COALESCE(SUM(aum_total), 0) as total_aum,
                ROUND(CAST(SUM(churn_flag) AS DOUBLE) / COUNT(*) * 100.0, 2) as churn_rate,
                ROUND(CAST(SUM(has_credit_card) AS DOUBLE) / COUNT(*) * 100.0, 2) as card_rate
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_str}
            """
            df_kpis = run_query(kpi_query, params)
            
            if df_kpis.empty or df_kpis["total_customers"].iloc[0] == 0:
                st.warning("⚠️ Không có dữ liệu khách hàng thỏa mãn bộ lọc hiện tại.")
                return
                
            kpis = {
                "total_customers": int(df_kpis["total_customers"].iloc[0]),
                "total_aum": float(df_kpis["total_aum"].iloc[0]),
                "churn_rate": float(df_kpis["churn_rate"].iloc[0]) if df_kpis["churn_rate"].iloc[0] is not None else 0.0,
                "card_rate": float(df_kpis["card_rate"].iloc[0]) if df_kpis["card_rate"].iloc[0] is not None else 0.0
            }
            
            # Query RFM Segment
            rfm_query = f"""
            SELECT 
                rfm_segment,
                COUNT(*) as customer_count,
                ROUND(SUM(aum_total) / 1000000000.0, 2) as total_aum_billion,
                ROUND(AVG(aum_total) / 1000000.0, 2) as avg_aum_million,
                ROUND(AVG(txn_count_30d), 1) as avg_txn_30d,
                ROUND(AVG(txn_amount_30d) / 1000000.0, 2) as avg_txn_amt_30d_million,
                COUNT(CASE WHEN has_credit_card = 0 THEN 1 END) as no_credit_card_cnt,
                COUNT(CASE WHEN churn_flag = 1 THEN 1 END) as churn_flag_cnt
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_str}
            GROUP BY rfm_segment
            """
            df_rfm = run_query(rfm_query, params)
            
            # Query AUM
            aum_query = f"""
            SELECT 
                aum_bucket,
                COUNT(*) as customer_count,
                ROUND(SUM(aum_total) / 1000000000.0, 2) as total_aum_billion
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_str}
            GROUP BY aum_bucket
            """
            df_aum = run_query(aum_query, params)
            
            # Query Channel
            channel_query = f"""
            SELECT 
                primary_channel,
                COUNT(*) as customer_count
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_str}
            GROUP BY primary_channel
            """
            df_channel = run_query(channel_query, params)
            
            # Query Branch
            branch_query = f"""
            SELECT 
                primary_branch_code,
                COUNT(*) as customer_count,
                ROUND(SUM(aum_total) / 1000000000.0, 2) as total_aum_billion
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_str}
            GROUP BY primary_branch_code
            ORDER BY customer_count DESC
            LIMIT 10
            """
            df_branch = run_query(branch_query, params)
            
        except Exception as e:
            st.error(f"❌ Lỗi khi tải dữ liệu từ Trino: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            is_mock = True
            kpis = mock.get_mock_overview_kpis()
            df_rfm = mock.get_mock_rfm_distribution()
            df_aum = mock.get_mock_aum_distribution()
            df_channel = mock.get_mock_channel_distribution()
            df_branch = mock.get_mock_branch_distribution()

    # 4. Render KPIs Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="👥 Tổng khách hàng", value=f"{kpis['total_customers']:,}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="💰 Tổng tài sản quản lý (AUM)", value=f"{kpis['total_aum'] / 1000000000000:.2f} Nghìn tỷ VND")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="📉 Tỷ lệ Churn Risk", value=f"{kpis['churn_rate']:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with col4:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.metric(label="💳 Tỷ lệ sở hữu Thẻ tín dụng", value=f"{kpis['card_rate']:.1f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # 5. RFM Segments Distribution
    st.write("### 🎖️ Phân tích hành vi Khách giữ chân (RFM)")
    # 11 nhóm RFM chuẩn theo ma trận RankRFM (xem code_etl/gold/mart360/customer_360.yml),
    # xếp từ tốt nhất -> kém nhất để biểu đồ hiển thị theo đúng thứ tự chất lượng khách hàng.
    rfm_order = [
        'Champions', 'Loyal Customers', 'Potential Loyalists', 'New Customers',
        'At Risk', 'Hibernating', 'Lost'
    ]
    df_rfm['rfm_segment'] = pd.Categorical(df_rfm['rfm_segment'], categories=rfm_order, ordered=True)
    df_rfm = df_rfm.sort_values('rfm_segment').dropna(subset=['rfm_segment'])

    rfm_colors_map = {
        'Champions': theme.COLOR_GOLD,
        'Loyal Customers': theme.COLOR_SECONDARY_GREEN,
        'Potential Loyalists': "#3a5a40",
        'New Customers': "#a3b18a",
        'At Risk': "#e63946",
        'Hibernating': "#6c757d",
        'Lost': "#343a40"
    }
    
    col_chart, col_table = st.columns([3, 2])
    with col_chart:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Số lượng khách hàng theo phân khúc RFM</h4>", unsafe_allow_html=True)
        fig_rfm = px.bar(
            df_rfm, 
            x='rfm_segment', 
            y='customer_count',
            text_auto='.3s',
            labels={'rfm_segment': 'Phân khúc RFM', 'customer_count': 'Số lượng khách hàng'},
            color='rfm_segment',
            color_discrete_map=rfm_colors_map
        )
        fig_rfm.update_layout(showlegend=False, margin=dict(t=10, b=0, l=0, r=0), plot_bgcolor='white')
        st.plotly_chart(fig_rfm, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_table:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Bảng chi tiết phân khúc RFM</h4>", unsafe_allow_html=True)
        df_rfm_display = df_rfm[['rfm_segment', 'customer_count', 'total_aum_billion', 'avg_txn_30d', 'churn_flag_cnt']].copy()
        df_rfm_display.columns = ['Phân khúc', 'Khách hàng', 'Tổng AUM (Tỷ)', 'Giao dịch TB (30d)', 'Số khách Churn']
        st.dataframe(df_rfm_display, hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 6. AUM Buckets and Channels Distribution
    col_aum, col_chan = st.columns(2)
    aum_colors_map = {
        'VIP': theme.COLOR_GOLD,
        'PRIORITY': theme.COLOR_SECONDARY_GREEN,
        'AFFLUENT': theme.COLOR_PRIMARY_NAVY,
        'MASS': "#a3b18a"
    }
    
    with col_aum:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Phân bổ Tổng AUM (Tỷ VND) theo nhóm tài sản</h4>", unsafe_allow_html=True)
        fig_aum = px.pie(
            df_aum, 
            values='total_aum_billion', 
            names='aum_bucket', 
            hole=0.4,
            color='aum_bucket',
            color_discrete_map=aum_colors_map
        )
        fig_aum.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_aum, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_chan:
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>Phân bổ theo Kênh giao dịch chính (30 ngày)</h4>", unsafe_allow_html=True)
        channel_colors = [theme.COLOR_PRIMARY_NAVY, theme.COLOR_SECONDARY_GREEN, theme.COLOR_GOLD, "#5c677d", "#abc4ff"]
        fig_chan = px.pie(
            df_channel, 
            values='customer_count', 
            names='primary_channel', 
            hole=0.4,
            color_discrete_sequence=channel_colors
        )
        fig_chan.update_layout(margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_chan, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 7. Top 10 Branches Analysis
    st.write("### 🏢 Phân phối tài sản theo Chi nhánh")
    branch_color_scale = [
        (0.0, theme.COLOR_PRIMARY_NAVY),
        (0.5, theme.COLOR_SECONDARY_GREEN),
        (1.0, theme.COLOR_GOLD)
    ]
    
    st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
    st.markdown("<h4>Top 10 Chi nhánh hàng đầu theo số lượng khách hàng & AUM</h4>", unsafe_allow_html=True)
    fig_branch = px.bar(
        df_branch,
        y='primary_branch_code',
        x='customer_count',
        text_auto='.3s',
        orientation='h',
        color='total_aum_billion',
        labels={
            'primary_branch_code': 'Mã chi nhánh', 
            'customer_count': 'Số lượng khách hàng',
            'total_aum_billion': 'AUM (Tỷ VND)'
        },
        color_continuous_scale=branch_color_scale
    )
    fig_branch.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=10, b=0, l=0, r=0), plot_bgcolor='white')
    st.plotly_chart(fig_branch, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
