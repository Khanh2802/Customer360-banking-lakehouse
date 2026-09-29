"""
Ánh xạ branch_code -> Tỉnh/Thành phố (Việt Nam) cho biểu đồ bản đồ (Trang 2 - RFM & Địa lý).

Bối cảnh: các trường `city`/`district` trong dim_customer_masked chỉ có 3-5 giá trị
duy nhất trên toàn bộ tập dữ liệu (quá thô, không phản ánh đúng phân bố chi nhánh thật),
trong khi `branch_code`/`primary_branch_code` có 51 mã, với 3 ký tự đầu (prefix) là mã
tỉnh/thành mà chi nhánh đang đặt trụ sở (vd HCM003, HAN010, DAN002...). Vì vậy ta dùng
prefix của mã chi nhánh để suy ra tỉnh/thành, thay vì dùng city/district.

Không cần file GeoJSON ranh giới tỉnh (nặng, khó nhúng) — chỉ cần toạ độ tâm (centroid)
mỗi tỉnh để vẽ bản đồ bong bóng (bubble map) bằng plotly Scattergeo.
"""

import re

# Toạ độ tâm (lat, lon) gần đúng của trung tâm hành chính mỗi tỉnh/thành,
# khớp với 12 prefix branch_code thực tế có trong dữ liệu đã upload.
PROVINCE_MAP = {
    "HCM": {"name": "TP. Hồ Chí Minh",     "region": "Nam Bộ",       "lat": 10.7769, "lon": 106.7009},
    "HAN": {"name": "Hà Nội",              "region": "Bắc Bộ",       "lat": 21.0285, "lon": 105.8542},
    "DAN": {"name": "Đà Nẵng",             "region": "Trung Bộ",     "lat": 16.0544, "lon": 108.2022},
    "HPG": {"name": "Hải Phòng",           "region": "Bắc Bộ",       "lat": 20.8449, "lon": 106.6881},
    "BDG": {"name": "Bình Dương",          "region": "Nam Bộ",       "lat": 11.3254, "lon": 106.4770},
    "KHH": {"name": "Khánh Hòa (Nha Trang)", "region": "Trung Bộ",   "lat": 12.2388, "lon": 109.1967},
    "HUE": {"name": "Thừa Thiên Huế",      "region": "Trung Bộ",     "lat": 16.4637, "lon": 107.5909},
    "QNI": {"name": "Bình Định (Quy Nhơn)", "region": "Trung Bộ",    "lat": 13.7757, "lon": 109.2219},
    "NAN": {"name": "Nghệ An (Vinh)",      "region": "Bắc Trung Bộ", "lat": 18.6699, "lon": 105.6813},
    "DNI": {"name": "Đồng Nai",            "region": "Nam Bộ",       "lat": 10.9574, "lon": 106.8426},
    "CTH": {"name": "Cần Thơ",             "region": "Tây Nam Bộ",   "lat": 10.0452, "lon": 105.7469},
    "NDH": {"name": "Nam Định",            "region": "Bắc Bộ",       "lat": 20.4388, "lon": 106.1621},
}

# Prefix mặc định khi gặp mã chi nhánh lạ (không nằm trong PROVINCE_MAP) — tránh vẽ lỗi bản đồ
_UNKNOWN = {"name": "Khác/Chưa xác định", "region": "N/A", "lat": None, "lon": None}


def extract_prefix(branch_code: str) -> str:
    """Lấy phần chữ cái đứng đầu mã chi nhánh, vd 'HCM003' -> 'HCM'."""
    if not branch_code or not isinstance(branch_code, str):
        return ""
    match = re.match(r"^[A-Za-z]+", branch_code.strip())
    return match.group(0).upper() if match else ""


def get_province(branch_code: str) -> dict:
    """Trả về dict {name, region, lat, lon} tương ứng với mã chi nhánh."""
    prefix = extract_prefix(branch_code)
    return PROVINCE_MAP.get(prefix, _UNKNOWN)


def attach_province_columns(df, branch_col: str = "primary_branch_code"):
    """
    Thêm các cột province_name/province_region/lat/lon vào DataFrame dựa theo branch_col.
    Không sửa DataFrame gốc — trả về bản sao.
    """
    df = df.copy()
    provinces = df[branch_col].apply(get_province)
    df["province_name"] = provinces.apply(lambda p: p["name"])
    df["province_region"] = provinces.apply(lambda p: p["region"])
    df["lat"] = provinces.apply(lambda p: p["lat"])
    df["lon"] = provinces.apply(lambda p: p["lon"])
    return df


def aggregate_by_province(df, branch_col: str = "primary_branch_code",
                           count_col: str = "customer_count", aum_col: str = "total_aum_billion"):
    """
    Nhận vào DataFrame đã group-by theo branch_code (có count_col, aum_col), gộp tiếp
    lên cấp tỉnh/thành (vì nhiều chi nhánh có thể cùng một tỉnh) để vẽ bản đồ.
    """
    df = attach_province_columns(df, branch_col=branch_col)
    df = df.dropna(subset=["lat", "lon"])
    agg = df.groupby(["province_name", "province_region", "lat", "lon"], as_index=False).agg(
        **{count_col: (count_col, "sum"), aum_col: (aum_col, "sum")}
    )
    return agg.sort_values(count_col, ascending=False)

# ---------------------------------------------------------------------------
# Ánh xạ theo cột `city` THẬT (dim_customer_masked.city) — theo yêu cầu dùng
# thẳng dữ liệu gốc thay vì suy diễn qua branch_code. Lưu ý: cột city trong dữ
# liệu nguồn (xem data_generator/sql_generators/oracle_gen.sql) chỉ được sinh
# tuần hoàn qua ĐÚNG 3 giá trị cố định — 'Ha Noi' / 'Ho Chi Minh' / 'Da Nang'
# (MOD(customer_id, 3), không liên quan đến branch_code thật của khách) — nên
# bản đồ theo city sẽ chỉ có tối đa 3 điểm, thô hơn bản đồ theo branch_code.
CITY_NAME_MAP = {
    "Ha Noi":       {"name": "Hà Nội",          "lat": 21.0285, "lon": 105.8542},
    "Ho Chi Minh":  {"name": "TP. Hồ Chí Minh", "lat": 10.7769, "lon": 106.7009},
    "Da Nang":      {"name": "Đà Nẵng",         "lat": 16.0544, "lon": 108.2022},
}

_UNKNOWN_CITY = {"name": "Khác/Chưa xác định", "lat": None, "lon": None}


def get_city_coords(city_raw: str) -> dict:
    """Trả về dict {name, lat, lon} tương ứng với giá trị thô của cột city."""
    if not city_raw or not isinstance(city_raw, str):
        return _UNKNOWN_CITY
    return CITY_NAME_MAP.get(city_raw.strip(), _UNKNOWN_CITY)


def aggregate_by_city(df, city_col: str = "city",
                       count_col: str = "customer_count", aum_col: str = "total_aum_billion"):
    """
    Nhận DataFrame đã group-by theo cột city thô (có count_col, aum_col), gắn
    tên hiển thị + toạ độ, loại các city lạ không map được, để vẽ bản đồ.
    """
    df = df.copy()
    coords = df[city_col].apply(get_city_coords)
    df["province_name"] = coords.apply(lambda c: c["name"])
    df["lat"] = coords.apply(lambda c: c["lat"])
    df["lon"] = coords.apply(lambda c: c["lon"])
    df = df.dropna(subset=["lat", "lon"])
    agg = df.groupby(["province_name", "lat", "lon"], as_index=False).agg(
        **{count_col: (count_col, "sum"), aum_col: (aum_col, "sum")}
    )
    return agg.sort_values(count_col, ascending=False)

