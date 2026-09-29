import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import run_query, get_latest_cob_dt
import mock_data as mock
import theme

def render_customer_profile(is_mock=False):
    # Form tìm kiếm dạng Slicer Card
    st.markdown("<div class='slicer-block'>", unsafe_allow_html=True)
    st.markdown("<h4 style='margin:0 0 10px 0; color:#0B1849;'>🔎 Tìm kiếm Khách hàng 360°</h4>", unsafe_allow_html=True)
    col_search, col_hint = st.columns([2, 3])
    with col_search:
        customer_id_input = st.text_input(
            "Nhập ID Khách hàng (Customer ID):",
            value="10001" if is_mock else "",
            placeholder="Ví dụ: 10001, 7920000001...",
            label_visibility="collapsed"
        )
    with col_hint:
        st.markdown("<span style='color: gray; font-size: 0.9rem; line-height: 2.5;'>💡 Bảng Gold lưu dữ liệu từ ID 10001 trở đi. Nhấn Enter hoặc nút bên cạnh.</span>", unsafe_allow_html=True)
    
    btn_search = st.button("Tìm kiếm Hồ sơ", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    
    if btn_search or customer_id_input:
        if not customer_id_input.strip().isdigit():
            st.warning("⚠️ Vui lòng nhập Customer ID hợp lệ (chỉ bao gồm chữ số).")
            return
            
        customer_id = int(customer_id_input.strip())
        
        # 1. Load Data
        profile = None
        if is_mock:
            profile = mock.get_mock_customer_profile(customer_id)
        else:
            try:
                # Lấy COB Date mới nhất (helper dùng chung — xem utils.get_latest_cob_dt)
                latest_cob = get_latest_cob_dt()
                
                # Query thông tin profile (Thử JOIN với campaign_target).
                # Dùng placeholder '?' (qmark) thay vì nối chuỗi giá trị trực tiếp vào SQL.
                query = """
                SELECT
                    m.customer_id,
                    m.full_name_masked,
                    m.age,
                    m.gender,
                    m.customer_segment,
                    m.primary_branch_code,
                    m.kyc_status,
                    m.total_accounts,
                    m.total_cards,
                    m.total_loans,
                    m.has_credit_card,
                    m.has_savings,
                    m.has_loan,
                    ROUND(m.aum_total / 1000000.0, 1)    AS aum_million_vnd,
                    m.aum_bucket,
                    ROUND(m.total_deposit_balance / 1000000.0, 1)  AS deposit_balance_million,
                    ROUND(m.total_loan_outstanding / 1000000.0, 1) AS loan_outstanding_million,
                    m.txn_count_30d,
                    ROUND(m.txn_amount_30d / 1000000.0, 1) AS txn_amount_30d_million,
                    m.days_since_last_txn,
                    m.primary_channel,
                    m.interaction_count_90d,
                    m.last_interaction_date,
                    m.rfm_recency_score,
                    m.rfm_frequency_score,
                    m.rfm_monetary_score,
                    m.rfm_segment,
                    m.churn_flag,
                    m.cross_sell_credit_card_flag
                FROM lakehouse.sandbox.mart_customer_360_masked m
                WHERE m.customer_id = ?
                  AND m.cob_dt = CAST(? AS DATE)
                """
                df_profile = run_query(query, (customer_id, latest_cob))
                
                if df_profile.empty:
                    st.error(f"❌ Không tìm thấy khách hàng có ID **{customer_id}** trong hệ thống live.")
                    return
                
                profile = df_profile.iloc[0].to_dict()
                
                # Thử lấy thêm thông tin chiến dịch đề xuất.
                # Đọc từ lakehouse.sandbox.campaign_target (lớp sandbox đã qua kiểm soát
                # truy cập chung, KHÔNG đọc thẳng lakehouse.gold.campaign_target) để đồng
                # nhất với mọi bảng khác trên dashboard — xem code_etl/shared/ops/pii_masking.py.
                try:
                    camp_query = """
                    SELECT campaign_type 
                    FROM lakehouse.sandbox.campaign_target 
                    WHERE customer_id = ?
                      AND cob_dt = CAST(? AS DATE)
                    """
                    df_camp = run_query(camp_query, (customer_id, latest_cob))
                    profile["recommended_campaign"] = df_camp["campaign_type"].iloc[0] if not df_camp.empty else None
                except Exception:
                    profile["recommended_campaign"] = None
                    
            except Exception as e:
                st.error(f"❌ Lỗi truy vấn dữ liệu từ Trino: {e}")
                st.warning("⚠️ Đang hiển thị kết quả từ **Dữ liệu Giả lập (Mock Data)**.")
                profile = mock.get_mock_customer_profile(customer_id)
        
        if profile:
            # 2. Render Profile Details
            seg_bg = theme.COLOR_GOLD if profile['customer_segment'] == 'VIP' else theme.COLOR_SECONDARY_GREEN if profile['customer_segment'] == 'PRIORITY' else "#5c677d"
            seg_txt = theme.COLOR_PRIMARY_NAVY if profile['customer_segment'] == 'VIP' else "#FFFFFF"
            
            # Header Profile
            st.markdown(f"""
            <div style='background-color: {theme.COLOR_PRIMARY_NAVY}; padding: 20px; border-radius: 10px; margin-bottom: 20px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                <div style='margin: 0; color: {theme.COLOR_GOLD} !important; font-size: 1.6rem; font-weight: 700; line-height: 1.3;'>👤 {profile['full_name_masked']}</div>
                <p style='margin: 8px 0 0 0; font-size: 1.1rem; color: {theme.COLOR_LIGHT_BG};'>
                    ID: <b>{profile['customer_id']}</b> | 
                    Phân khúc: <span style="background-color: {seg_bg}; color: {seg_txt}; padding: 3px 10px; border-radius: 5px; font-weight: bold;">{profile['customer_segment']}</span> | 
                    Giới tính: <b>{profile['gender']}</b> | Tuổi: <b>{profile['age']}</b> | 
                    Chi nhánh: <b>{profile['primary_branch_code']}</b> | KYC: <b>{profile['kyc_status']}</b>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Row 1: Products Holding Badges & Financial Info (PowerBI Cards)
            col_prod, col_fin = st.columns([1, 1])
            with col_prod:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                st.markdown("<h4>💳 Trạng thái sở hữu Sản phẩm</h4>", unsafe_allow_html=True)
                
                def get_status_html(has_product):
                    return f'<span style="background-color: {theme.COLOR_SECONDARY_GREEN}; color: white; padding: 4px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8rem;">ĐANG SỬ DỤNG</span>' if has_product == 1 else '<span style="background-color: #e63946; color: white; padding: 4px 10px; border-radius: 15px; font-weight: bold; font-size: 0.8rem;">CHƯA CÓ</span>'
                
                st.markdown(f"""
                <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                    <tr style="border-bottom: 1px solid #eee; height: 45px;">
                        <td>🏦 <b>Tài khoản CASA:</b></td>
                        <td style="text-align: right;">{get_status_html(1 if profile['total_accounts'] > 0 else 0)}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 45px;">
                        <td>📈 <b>Sổ tiết kiệm (Savings):</b></td>
                        <td style="text-align: right;">{get_status_html(profile['has_savings'])}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 45px;">
                        <td>🏠 <b>Khoản vay (Loans):</b></td>
                        <td style="text-align: right;">{get_status_html(profile['has_loan'])}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 45px;">
                        <td>💳 <b>Thẻ tín dụng (Credit Card):</b></td>
                        <td style="text-align: right;">{get_status_html(profile['has_credit_card'])}</td>
                    </tr>
                </table>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
            with col_fin:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                st.markdown("<h4>💰 Tài sản quản lý & Dư nợ</h4>", unsafe_allow_html=True)
                
                fig_fin = go.Figure()
                fig_fin.add_trace(go.Indicator(
                    mode = "number",
                    value = profile['aum_million_vnd'],
                    title = {"text": "Tổng tài sản (AUM)"},
                    number = {'suffix': ' Tr. VND', 'valueformat': ',.1f', 'font': {'color': theme.COLOR_PRIMARY_NAVY, 'size': 32}},
                    domain = {'x': [0, 1], 'y': [0.4, 1]}
                ))
                fig_fin.update_layout(height=130, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig_fin, use_container_width=True)
                
                col_dep, col_loan = st.columns(2)
                with col_dep:
                    st.metric("Tiền gửi & Tiết kiệm", f"{profile['deposit_balance_million']:,} Tr. VND")
                with col_loan:
                    st.metric("Dư nợ cho vay", f"{profile['loan_outstanding_million']:,} Tr. VND")
                st.markdown("</div>", unsafe_allow_html=True)

            # Row 2: RFM Segment & Behavioral
            col_rfm, col_beh = st.columns([1, 1])
            with col_rfm:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                st.markdown("<h4>🎖️ Phân khúc & Điểm RFM</h4>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div style="background-color: {theme.COLOR_LIGHT_BG}; padding: 15px; border-radius: 6px; border-left: 5px solid {theme.COLOR_PRIMARY_NAVY}; margin-bottom: 15px;">
                    <p style="margin: 0; font-size: 0.85rem; color: #555;">Phân khúc RFM (30 ngày)</p>
                    <h4 style="margin: 3px 0 0 0; color: {theme.COLOR_PRIMARY_NAVY}; font-weight: bold; border-bottom: none !important; padding-bottom: 0 !important;">{profile['rfm_segment']}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("**Chi tiết điểm số (Thang 1-5):**")
                def make_score_bar(score, name):
                    stars = "★" * score + "☆" * (5 - score)
                    return f"**{name}**: &nbsp;&nbsp;&nbsp;&nbsp; <span style='font-size: 1.15rem; color: {theme.COLOR_GOLD};'>{stars}</span> ({score}/5)"
                
                st.markdown(make_score_bar(profile['rfm_recency_score'], "R - Recency"), unsafe_allow_html=True)
                st.markdown(make_score_bar(profile['rfm_frequency_score'], "F - Frequency"), unsafe_allow_html=True)
                st.markdown(make_score_bar(profile['rfm_monetary_score'], "M - Monetary"), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with col_beh:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                st.markdown("<h4>⚡ Hành vi Giao dịch (30 ngày)</h4>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                    <tr style="border-bottom: 1px solid #eee; height: 40px;">
                        <td><b>Số giao dịch (30d):</b></td>
                        <td style="text-align: right; font-weight: bold;">{profile['txn_count_30d']}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 40px;">
                        <td><b>Doanh số GD (30d):</b></td>
                        <td style="text-align: right; font-weight: bold;">{profile['txn_amount_30d_million']:,} Tr. VND</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 40px;">
                        <td><b>Số ngày không GD:</b></td>
                        <td style="text-align: right; font-weight: bold; color: {'red' if profile['days_since_last_txn'] > 90 else 'black'};">{profile['days_since_last_txn']} ngày</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 40px;">
                        <td><b>Kênh chính:</b></td>
                        <td style="text-align: right; font-weight: bold; color: {theme.COLOR_SECONDARY_GREEN};">{profile['primary_channel']}</td>
                    </tr>
                </table>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Row 3: Marketing Campaign & CRM
            col_camp, col_crm = st.columns([1, 1])
            with col_camp:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                st.markdown("<h4>🎯 Đề xuất Chiến dịch & Cơ hội bán</h4>", unsafe_allow_html=True)
                
                st.markdown("##### Bán chéo & Giữ chân:")
                if profile['cross_sell_credit_card_flag'] == 1:
                    st.success("💡 Mời mở thẻ tín dụng (Cross-sell Credit Card)")
                else:
                    st.info("ℹ️ Đã có thẻ hoặc chưa đạt tiêu chuẩn AUM.")
                    
                if profile['churn_flag'] == 1:
                    st.error("🚨 Khách có nguy cơ rời bỏ (Churn Risk)")
                else:
                    st.success("✅ Khách hoạt động ổn định (Active)")
                
                st.markdown("##### Chiến dịch đề xuất:")
                if profile.get('recommended_campaign'):
                    st.warning(f"📣 {profile['recommended_campaign']}")
                else:
                    st.info("Không có chiến dịch phù hợp tháng này.")
                st.markdown("</div>", unsafe_allow_html=True)

            with col_crm:
                st.markdown("<div class='powerbi-card'>", unsafe_allow_html=True)
                st.markdown("<h4>📞 Tương tác & Chăm sóc (CRM)</h4>", unsafe_allow_html=True)
                st.markdown(f"""
                <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
                    <tr style="border-bottom: 1px solid #eee; height: 45px;">
                        <td><b>Số lần tương tác (90d):</b></td>
                        <td style="text-align: right; font-weight: bold;">{profile['interaction_count_90d']} lần</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #eee; height: 45px;">
                        <td><b>Lần tương tác cuối:</b></td>
                        <td style="text-align: right; font-weight: bold;">{profile['last_interaction_date'] if profile['last_interaction_date'] else 'Không có dữ liệu'}</td>
                    </tr>
                </table>
                """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
