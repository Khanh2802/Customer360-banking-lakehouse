# Cấu hình bảng màu của dự án từ Color Hunt và Kiểu dáng PowerBI
# Palette: https://colorhunt.co/palette/0b1849124d1ce4b028ebede3

# Định nghĩa các màu chủ đạo
COLOR_PRIMARY_NAVY = "#0B1849"     # Xanh dương đậm (Bảng điều khiển & Header)
COLOR_SECONDARY_GREEN = "#124D1C"  # Xanh lá cây đậm (Chỉ số tài chính & Tăng trưởng)
COLOR_GOLD = "#E4B028"             # Vàng gold (Nhấn mạnh, VIP, Hover)
COLOR_LIGHT_BG = "#EBEDE3"         # Màu nền kem sáng
COLOR_APP_BG = "#F3F4F6"           # Màu nền xám nhạt toàn trang giống PowerBI
COLOR_WHITE = "#FFFFFF"
COLOR_BORDER = "#E5E7EB"

# Bảng màu cho biểu đồ Plotly
PLOTLY_THEME_COLORS = [
    COLOR_PRIMARY_NAVY,
    COLOR_SECONDARY_GREEN,
    COLOR_GOLD,
    "#3a5a40",  # Biến thể xanh lá
    "#1d3557",  # Biến thể xanh dương
    "#a3b18a",  # Biến thể xám xanh
    "#dad7cd"   # Biến thể cát sáng
]

# CSS nâng cấp giao diện Streamlit theo phong cách PowerBI chuyên nghiệp
CUSTOM_CSS = f"""
<style>
    /* 1. Nền tổng thể của ứng dụng (màu xám nhạt giống PowerBI) */
    [data-testid="stAppViewContainer"] {{
        background-color: {COLOR_APP_BG} !important;
        font-family: 'Segoe UI', Inter, Roboto, sans-serif !important;
    }}
    
    [data-testid="stHeader"] {{
        background-color: {COLOR_APP_BG} !important;
    }}
    
    /* 2. Sửa lỗi text trên sidebar có màu sáng để tương phản tốt với nền Navy của config.toml */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] div {{
        color: #FFFFFF !important;
    }}
    
    /* Input/selectbox trong sidebar */
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] div[role="listbox"] {{
        color: #333333 !important;
    }}
    
    /* 3. Tiêu đề trang */
    h1 {{
        color: {COLOR_PRIMARY_NAVY} !important;
        font-weight: 700 !important;
        border-bottom: 2px solid {COLOR_GOLD};
        padding-bottom: 8px;
        margin-bottom: 20px;
    }}
    
    h2, h3 {{
        color: {COLOR_PRIMARY_NAVY} !important;
        font-weight: 600 !important;
    }}

    /* 4. Khung đồ thị kiểu PowerBI Card (Trắng, viền, bo góc, bóng đổ) */
    .powerbi-card {{
        background-color: {COLOR_WHITE} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 8px !important;
        padding: 20px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03) !important;
        margin-bottom: 20px !important;
        color: #333333;
    }}
    
    .powerbi-card h4 {{
        margin-top: 0 !important;
        color: {COLOR_PRIMARY_NAVY} !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #F3F4F6 !important;
        padding-bottom: 8px !important;
        margin-bottom: 12px !important;
    }}

    /* 5. Khung chứa Slicer (Bộ lọc ngang ở trên cùng) */
    .slicer-block {{
        background-color: {COLOR_WHITE} !important;
        border: 1px solid {COLOR_BORDER} !important;
        border-radius: 6px !important;
        padding: 15px 20px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }}
    
    .slicer-title {{
        font-weight: 600 !important;
        color: {COLOR_PRIMARY_NAVY} !important;
        font-size: 0.95rem !important;
        margin-bottom: 8px !important;
    }}

    /* 6. Tối ưu độ tương phản cho Dropdown/Multiselect Slicer */
    /* Màu nhãn trên đỉnh Slicer */
    .slicer-block label p, 
    .slicer-block label span,
    .slicer-block label {{
        color: {COLOR_PRIMARY_NAVY} !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }}
    
    /* Màu của các thẻ tag đã chọn trong st.multiselect */
    span[data-baseweb="tag"] {{
        background-color: {COLOR_PRIMARY_NAVY} !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
    }}
    span[data-baseweb="tag"] span {{
        color: #FFFFFF !important;
    }}
    
    /* Màu chữ hiển thị trong danh sách scrolldown (Dropdown Listbox) */
    div[role="listbox"] ul li,
    div[role="listbox"] div,
    ul[role="listbox"] li,
    li[role="option"] div,
    li[role="option"] span {{
        color: #1F2937 !important; /* Chữ xám đậm/đen dễ nhìn */
        background-color: #FFFFFF !important;
    }}
    
    /* Hiệu ứng hover trong danh sách */
    li[role="option"]:hover,
    li[role="option"]:hover div {{
        background-color: #F3F4F6 !important;
    }}

    /* 6b. Sửa lỗi ô nhập liệu (vd. ô tìm Customer ID) bị "chìm chữ": Streamlit áp
    secondaryBackgroundColor (Navy — vốn định nghĩa riêng cho Sidebar trong
    .streamlit/config.toml) làm nền cho MỌI widget input trên toàn trang, kể cả
    ngoài sidebar, trong khi textColor (charcoal) vẫn giữ nguyên → chữ tối trên
    nền tối, gần như không đọc được. Ép nền trắng + chữ tối rõ ràng cho các ô
    nhập liệu và khung đóng (chưa mở dropdown) của multiselect/selectbox. */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-baseweb="input"] input {{
        background-color: {COLOR_WHITE} !important;
        color: #1F2937 !important;
        border: 1px solid {COLOR_BORDER} !important;
        caret-color: #1F2937 !important;
    }}

    [data-testid="stTextInput"] input::placeholder,
    [data-testid="stNumberInput"] input::placeholder {{
        color: #9CA3AF !important;
        opacity: 1 !important;
    }}

    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stSelectbox"] > div > div,
    [data-baseweb="select"] > div {{
        background-color: {COLOR_WHITE} !important;
        color: #1F2937 !important;
    }}

    /* 7. Nút chính (Primary buttons) */
    div.stButton > button:first-child {{
        background-color: {COLOR_SECONDARY_GREEN} !important;
        color: {COLOR_WHITE} !important;
        border: 1px solid {COLOR_SECONDARY_GREEN} !important;
        border-radius: 5px;
        font-weight: bold;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }}
    div.stButton > button:first-child:hover {{
        background-color: {COLOR_GOLD} !important;
        color: {COLOR_PRIMARY_NAVY} !important;
        border-color: {COLOR_GOLD} !important;
        transform: translateY(-1px);
    }}

    /* 8. Khung chỉ số metric */
    [data-testid="stMetricValue"] {{
        color: {COLOR_SECONDARY_GREEN} !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {COLOR_PRIMARY_NAVY} !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }}
</style>
"""

def inject_theme_css(st_instance):
    """Tiêm CSS tùy biến vào Streamlit."""
    st_instance.markdown(CUSTOM_CSS, unsafe_allow_html=True)
