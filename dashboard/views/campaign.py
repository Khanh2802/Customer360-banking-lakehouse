import streamlit as st
import pandas as pd
from utils import run_query, get_latest_cob_dt
import mock_data as mock
import theme

def render_campaign(is_mock=False):
    st.subheader("🎯 Công cụ Bán chéo & Chiến dịch Marketing (Campaign Segmenter)")
    st.write("Lọc danh sách khách hàng tiềm năng cho các chiến dịch kinh doanh dựa trên các thuộc tính của tệp Gold Layer.")
    
    # 1. PowerBI Slicer Bar (Bộ lọc ngang chứa các st.multiselect cuộn xuống được)
    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    col_rfm, col_aum, col_cc, col_churn = st.columns(4)
    
    # 11 nhóm RFM chuẩn theo ma trận RankRFM (đồng bộ với code_etl/gold/mart360/customer_360.yml)
    rfm_options = [
        "Champions", "Loyal Customers", "Potential Loyalists", "New Customers",
        "At Risk", "Hibernating", "Lost"
    ]
    aum_options = ["VIP", "PRIORITY", "AFFLUENT", "MASS"]
    cc_options = ["Đã có thẻ (1)", "Chưa có thẻ (0)"]
    churn_options = ["Có nguy cơ (1)", "Hoạt động tốt (0)"]
    
    with col_rfm:
        selected_rfm = st.multiselect("Slicer: Phân khúc RFM", options=rfm_options, default=rfm_options, key="camp_ms_rfm")
        
    with col_aum:
        selected_aum = st.multiselect("Slicer: Nhóm tài sản (AUM)", options=aum_options, default=aum_options, key="camp_ms_aum")
        
    with col_cc:
        selected_cc_labels = st.multiselect("Slicer: Thẻ tín dụng", options=cc_options, default=cc_options, key="camp_ms_cc")
        
    with col_churn:
        selected_churn_labels = st.multiselect("Slicer: Churn Risk", options=churn_options, default=churn_options, key="camp_ms_churn")
            
    st.markdown("</div>", unsafe_allow_html=True)

    # Map text values to numeric filters
    selected_cc = []
    for label in selected_cc_labels:
        if "Đã có" in label:
            selected_cc.append(1)
        if "Chưa có" in label:
            selected_cc.append(0)
            
    selected_churn = []
    for label in selected_churn_labels:
        if "Có nguy cơ" in label:
            selected_churn.append(1)
        if "Hoạt động tốt" in label:
            selected_churn.append(0)

    # Nếu không tích chọn mục nào, tự động kích hoạt tất cả để tránh lỗi trống
    if not selected_rfm:
        selected_rfm = rfm_options
    if not selected_aum:
        selected_aum = aum_options
    if not selected_cc:
        selected_cc = [0, 1]
    if not selected_churn:
        selected_churn = [0, 1]

    # 2. Xây dựng bộ lọc SQL động hoặc Giả lập
    df_filtered = pd.DataFrame()
    
    if is_mock:
        df_filtered = mock.get_mock_campaign_customers(None, None, None)
        df_filtered = df_filtered[
            (df_filtered["rfm_segment"].isin(selected_rfm)) & 
            (df_filtered["aum_bucket"].isin(selected_aum)) & 
            (df_filtered["has_credit_card"].isin(selected_cc)) & 
            (df_filtered["churn_flag"].isin(selected_churn))
        ]
    else:
        try:
            # Lấy COB Date mới nhất (helper dùng chung — xem utils.get_latest_cob_dt)
            latest_cob = get_latest_cob_dt()

            # Dùng placeholder '?' (qmark) thay vì nối chuỗi giá trị trực tiếp vào SQL —
            # tránh SQL injection và tách rõ code khỏi data.
            params = [latest_cob]
            conditions = ["cob_dt = CAST(? AS DATE)"]

            rfm_placeholders = ",".join(["?"] * len(selected_rfm))
            conditions.append(f"rfm_segment IN ({rfm_placeholders})")
            params.extend(selected_rfm)

            aum_placeholders = ",".join(["?"] * len(selected_aum))
            conditions.append(f"aum_bucket IN ({aum_placeholders})")
            params.extend(selected_aum)

            cc_placeholders = ",".join(["?"] * len(selected_cc))
            conditions.append(f"has_credit_card IN ({cc_placeholders})")
            params.extend(selected_cc)

            churn_placeholders = ",".join(["?"] * len(selected_churn))
            conditions.append(f"churn_flag IN ({churn_placeholders})")
            params.extend(selected_churn)

            where_clause = " AND ".join(conditions)
            params = tuple(params)
            
            query = f"""
            SELECT 
                customer_id,
                full_name_masked,
                age,
                gender,
                customer_segment,
                aum_bucket,
                rfm_segment,
                ROUND(aum_total / 1000000.0, 1) as aum_million_vnd,
                has_credit_card,
                churn_flag
            FROM lakehouse.sandbox.mart_customer_360_masked
            WHERE {where_clause}
            ORDER BY aum_total DESC
            LIMIT 1000
            """
            
            df_filtered = run_query(query, params)
            
        except Exception as e:
            st.error(f"❌ Lỗi truy vấn danh sách khách hàng từ Trino: {e}")
            st.warning("⚠️ Đang tự động chuyển sang chế độ **Dữ liệu Giả lập (Mock Data)**.")
            df_filtered = mock.get_mock_campaign_customers(None, None, None)
            df_filtered = df_filtered[
                (df_filtered["rfm_segment"].isin(selected_rfm)) & 
                (df_filtered["aum_bucket"].isin(selected_aum)) & 
                (df_filtered["has_credit_card"].isin(selected_cc)) & 
                (df_filtered["churn_flag"].isin(selected_churn))
            ]

    # 3. Render Results
    if not df_filtered.empty:
        total_leads = len(df_filtered)
        total_lead_aum = df_filtered["aum_million_vnd"].sum()
        
        c_l1, c_l2 = st.columns(2)
        with c_l1:
            st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
            st.metric("🎯 Quy mô tệp khách hàng thỏa mãn", f"{total_leads:,} khách hàng")
            st.markdown("</div>", unsafe_allow_html=True)
        with c_l2:
            st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
            st.metric("💰 Tổng tài sản (AUM) tệp lọc", f"{total_lead_aum / 1000:.2f} Tỷ VND")
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Hiển thị DataFrame trong Card
        st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
        st.markdown("<h4>🔍 Danh sách khách hàng mục tiêu (Hiển thị tối đa 1000 khách)</h4>", unsafe_allow_html=True)
        
        df_display = df_filtered.copy()
        df_display.columns = [
            "Customer ID", "Họ tên (Masked)", "Tuổi", "Giới tính", 
            "Phân khúc", "AUM Bucket", "RFM Segment", "AUM (Tr. VND)", 
            "Sở hữu thẻ tín dụng", "Nguy cơ Churn"
        ]
        
        st.dataframe(df_display, hide_index=True, use_container_width=True)
        
        # Download Button
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Tải xuống danh sách (CSV)",
            data=csv,
            file_name="campaign_leads.csv",
            mime="text/csv",
            type="primary"
        )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ Không tìm thấy khách hàng nào thỏa mãn điều kiện lọc.")
