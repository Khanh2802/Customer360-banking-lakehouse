import streamlit as st
import os

# Set page configuration - must be the first streamlit call
st.set_page_config(
    page_title="Customer 360 Lakehouse Dashboard",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thêm views và utils vào python path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "views"))

from theme import inject_theme_css
# Tiêm bảng màu tùy biến
inject_theme_css(st)

from views.overview import render_overview
from views.eda import render_eda
from views.rfm_geo import render_rfm_geo
from views.cohort import render_cohort
from views.customer_profile import render_customer_profile
from views.campaign import render_campaign
from views.cross_sell import render_cross_sell
from views.ops_health import render_ops_health
from utils import clear_query_cache

# Cấu hình sidebar
st.sidebar.markdown("""
<div style="text-align: center; padding-bottom: 20px;">
    <h2 style="color: #FFFFFF; margin-bottom: 0;">🏦 Ngân hàng Bán lẻ</h2>
    <p style="color: #ff6e40; font-weight: bold; margin-top: 5px; font-size: 1.1rem;">Customer 360 Lakehouse</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.title("🧭 Điều hướng")
page = st.sidebar.radio(
    "Chọn trang hiển thị:",
    [
        "🏠 Tổng quan",
        "🧬 EDA & Nhân khẩu học",
        "🗺️ RFM & Địa lý",
        "📈 Phân tích Cohort",
        "🔎 Hồ sơ Khách hàng 360°",
        "🎯 Chiến dịch & Bán chéo",
        "📊 Cơ hội Bán chéo Sản phẩm",
        "⚙️ Sức khỏe Pipeline ETL",
    ]
)

st.sidebar.markdown("---")
st.sidebar.title("⚙️ Cấu hình kết nối")

# Lựa chọn kết nối: live Trino hoặc dùng mock data
connection_mode = st.sidebar.radio(
    "Chế độ dữ liệu:",
    ["Kết nối Trino Live (Docker Stack)", "Dùng dữ liệu Giả lập (Mock Data)"],
    help="Trần trừ gì nữa! Chuyển sang dữ liệu Mock nếu bạn chưa bật Docker."
)
is_mock = (connection_mode == "Dùng dữ liệu Giả lập (Mock Data)")

if not is_mock:
    st.sidebar.success("🔗 Đang cố kết nối: trino://localhost:8085")
else:
    st.sidebar.warning("⚠️ Chế độ Dữ liệu Giả lập (Offline)")

# Button xóa cache
if st.sidebar.button("🔄 Làm mới dữ liệu (Clear Cache)"):
    clear_query_cache()
    st.sidebar.info("Đã xóa cache dữ liệu thành công!")

# Phần Footer của Sidebar
st.sidebar.markdown("""
---
<div style="text-align: center; color: gray; font-size: 0.8rem; padding-top: 30px;">
    <p>Hệ thống xây dựng trên:<br><b>Apache Iceberg + Spark + Trino + Airflow</b></p>
    <p>© 2026 Lakehouse Analytics Team</p>
</div>
""", unsafe_allow_html=True)

# Main Application Hub
st.title("🏦 Hệ thống Phân tích Khách hàng 360° (Lakehouse)")

if page == "🏠 Tổng quan":
    render_overview(is_mock=is_mock)
elif page == "🧬 EDA & Nhân khẩu học":
    render_eda(is_mock=is_mock)
elif page == "🗺️ RFM & Địa lý":
    render_rfm_geo(is_mock=is_mock)
elif page == "📈 Phân tích Cohort":
    render_cohort(is_mock=is_mock)
elif page == "🔎 Hồ sơ Khách hàng 360°":
    render_customer_profile(is_mock=is_mock)
elif page == "🎯 Chiến dịch & Bán chéo":
    render_campaign(is_mock=is_mock)
elif page == "📊 Cơ hội Bán chéo Sản phẩm":
    render_cross_sell(is_mock=is_mock)
elif page == "⚙️ Sức khỏe Pipeline ETL":
    render_ops_health(is_mock=is_mock)
