import pandas as pd
import numpy as np

def get_mock_overview_kpis():
    return {
        "total_customers": 10000,
        "total_aum": 3456278900000.0, # ~3.45 Trillion VND
        "churn_rate": 8.5, # 8.5%
        "card_rate": 22.4 # 22.4%
    }

def get_mock_rfm_distribution():
    # 7 nhóm RFM CHUẨN thực tế theo code_etl/gold/segmentation/rfm_segment.yml
    # (KHÔNG phải danh sách 11 nhóm cũ — đã đối chiếu và sửa lại cho khớp với
    # taxonomy thật của pipeline: Champions/Loyal Customers/Potential Loyalists/
    # New Customers/At Risk/Hibernating/Lost), xếp từ tốt nhất đến kém nhất theo
    # rfm_score.
    data = {
        "rfm_segment": [
            "Champions", "Loyal Customers", "Potential Loyalists",
            "New Customers", "At Risk", "Hibernating", "Lost"
        ],
        "customer_count":          [900,    1800,   2400,  1200,  1800,  1200,  700],
        "total_aum_billion":       [1350.0, 1700.0, 1100.0, 280.0, 580.0, 210.0, 60.0],
        "avg_aum_million":         [1500.0, 944.0,  458.0, 233.0, 322.0, 175.0, 86.0],
        "avg_txn_30d":             [40.0,   28.0,   18.0,  10.0,  5.0,   1.5,   0.3],
        "avg_txn_amt_30d_million": [25.0,   14.0,   8.0,   4.0,   2.0,   0.6,   0.1],
        "no_credit_card_cnt":      [90,     350,    950,   650,   1350,  1050,  620],
        "churn_flag_cnt":          [0,      10,     60,    20,    850,   1050,  650]
    }
    return pd.DataFrame(data)

def get_mock_aum_distribution():
    data = {
        "aum_bucket": ["VIP", "PRIORITY", "AFFLUENT", "MASS"],
        "customer_count": [500, 2500, 4000, 3000],
        "total_aum_billion": [2150.0, 1050.0, 220.0, 36.278]
    }
    return pd.DataFrame(data)

def get_mock_channel_distribution():
    data = {
        "primary_channel": ["MOBILE_BANKING", "INTERNET_BANKING", "ATM", "POS", "BRANCH"],
        "customer_count": [5800, 1800, 1200, 800, 400]
    }
    return pd.DataFrame(data)

def get_mock_product_penetration():
    data = [
        {"customer_segment": "VIP", "aum_bucket": "VIP", "total": 500, "pct_has_credit_card": 85.0, "pct_has_savings": 95.0, "pct_has_loan": 45.0, "opportunity_cc": 75, "opportunity_deposit": 25, "opportunity_loan": 275, "cc_opportunity_aum_billion": 322.5, "cc_opportunity_active_30d": 70, "estimated_fee_revenue_million_vnd": 4.5},
        {"customer_segment": "PRIORITY", "aum_bucket": "PRIORITY", "total": 2500, "pct_has_credit_card": 65.0, "pct_has_savings": 80.0, "pct_has_loan": 30.0, "opportunity_cc": 875, "opportunity_deposit": 500, "opportunity_loan": 1750, "cc_opportunity_aum_billion": 367.5, "cc_opportunity_active_30d": 780, "estimated_fee_revenue_million_vnd": 52.5},
        {"customer_segment": "RETAIL", "aum_bucket": "AFFLUENT", "total": 4000, "pct_has_credit_card": 40.0, "pct_has_savings": 60.0, "pct_has_loan": 20.0, "opportunity_cc": 2400, "opportunity_deposit": 1600, "opportunity_loan": 3200, "cc_opportunity_aum_billion": 132.0, "cc_opportunity_active_30d": 1800, "estimated_fee_revenue_million_vnd": 144.0},
        {"customer_segment": "RETAIL", "aum_bucket": "MASS", "total": 3000, "pct_has_credit_card": 15.0, "pct_has_savings": 35.0, "pct_has_loan": 10.0, "opportunity_cc": 2550, "opportunity_deposit": 1950, "opportunity_loan": 2700, "cc_opportunity_aum_billion": 30.8, "cc_opportunity_active_30d": 1200, "estimated_fee_revenue_million_vnd": 153.0}
    ]
    return pd.DataFrame(data)

def get_mock_branch_distribution():
    data = {
        "primary_branch_code": ["HCM001", "HN001", "HCM002", "DN001", "HN002", "HP001", "CT001", "HCM003", "HN003", "BD001"],
        "customer_count": [1500, 1400, 1100, 900, 850, 700, 650, 600, 500, 480],
        "total_aum_billion": [550.2, 510.5, 380.1, 290.4, 270.2, 210.1, 185.3, 160.2, 140.5, 120.4]
    }
    return pd.DataFrame(data)

def get_mock_customer_profile(customer_id):
    # Determine gender and names based on ID
    np.random.seed(int(customer_id) % 1000)
    genders = ["M", "F"]  # khớp dữ liệu thật: gender CHAR(1) IN ('M','F','O')
    gender = np.random.choice(genders)
    
    first_names = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ"]
    mid_names = ["Văn", "Thị", "Minh", "Hữu", "Đức", "Kim", "Anh"]
    last_names = ["An", "Bình", "Chương", "Dương", "Hải", "Khánh", "Linh", "Nam", "Sơn", "Vy"]
    
    name = f"{np.random.choice(first_names)} {np.random.choice(mid_names)} {np.random.choice(last_names)}"
    name_masked = name.split()[0] + " " + " ".join([n[0] + "**" for n in name.split()[1:]])
    
    segments = ["RETAIL", "PRIORITY", "VIP"]
    aum_buckets = ["MASS", "AFFLUENT", "PRIORITY", "VIP"]
    # 7 nhóm RFM chuẩn thực tế theo code_etl/gold/segmentation/rfm_segment.yml
    rfm_segments = [
        "Champions", "Loyal Customers", "Potential Loyalists",
        "New Customers", "At Risk", "Hibernating", "Lost"
    ]
    
    idx = int(customer_id) % len(segments)
    segment = segments[idx]
    
    aum_idx = (int(customer_id) % len(aum_buckets))
    aum_bucket = aum_buckets[aum_idx]
    
    rfm_idx = (int(customer_id) % len(rfm_segments))
    rfm_segment = rfm_segments[rfm_idx]
    
    aum_val = float(np.random.randint(5, 5500) * 1000000)
    if aum_bucket == "VIP":
        aum_val = float(np.random.randint(5000, 15000) * 1000000)
    elif aum_bucket == "PRIORITY":
        aum_val = float(np.random.randint(1000, 5000) * 1000000)
    elif aum_bucket == "AFFLUENT":
        aum_val = float(np.random.randint(100, 1000) * 1000000)
    else:
        aum_val = float(np.random.randint(5, 100) * 1000000)
        
    has_cc = 1 if np.random.rand() > 0.4 else 0
    has_save = 1 if np.random.rand() > 0.3 else 0
    has_loan = 1 if np.random.rand() > 0.8 else 0
    
    total_acc = has_save + has_loan + np.random.randint(1, 3)
    total_cards = has_cc + np.random.randint(1, 2)
    
    campaigns = ["Mở thẻ tín dụng hoàn tiền", "Vay mua nhà ưu đãi", "Gửi tiết kiệm lãi suất kép", "Nâng hạng VIP/Priority", "None"]
    campaign = np.random.choice(campaigns)
    
    profile = {
        "customer_id": int(customer_id),
        "full_name_masked": name_masked,
        "age": np.random.randint(22, 75),
        "gender": gender,
        "customer_segment": segment,
        "primary_branch_code": f"{np.random.choice(['HCM', 'HN', 'DN', 'HP', 'CT'])}{np.random.randint(10, 99):03d}",
        "kyc_status": "VERIFIED" if np.random.rand() > 0.1 else "PENDING",
        "total_accounts": total_acc,
        "total_cards": total_cards,
        "total_loans": has_loan,
        "has_credit_card": has_cc,
        "has_savings": has_save,
        "has_loan": has_loan,
        "aum_million_vnd": round(aum_val / 1000000, 1),
        "aum_bucket": aum_bucket,
        "deposit_balance_million": round(aum_val * 0.95 / 1000000, 1) if has_save else round(aum_val * 0.1 / 1000000, 1),
        "loan_outstanding_million": round(np.random.randint(50, 1000) * 1000000 / 1000000, 1) if has_loan else 0.0,
        "txn_count_30d": np.random.randint(0, 80),
        "txn_amount_30d_million": round(np.random.randint(1, 50) * 1000000 / 1000000, 1),
        "days_since_last_txn": np.random.randint(0, 120),
        "primary_channel": np.random.choice(["MOBILE_BANKING", "INTERNET_BANKING", "ATM", "POS", "BRANCH"]),
        "interaction_count_90d": np.random.randint(0, 12),
        "last_interaction_date": "2025-12-28 14:30:00",
        "rfm_recency_score": np.random.randint(1, 6),
        "rfm_frequency_score": np.random.randint(1, 6),
        "rfm_monetary_score": np.random.randint(1, 6),
        "rfm_segment": rfm_segment,
        "churn_flag": 1 if np.random.randint(0, 120) > 90 else 0,
        "cross_sell_credit_card_flag": 1 if (aum_val >= 100000000 and has_cc == 0) else 0,
        "recommended_campaign": campaign if campaign != "None" else None
    }
    return profile

def get_mock_campaign_customers(rfm_segment=None, aum_bucket=None, has_credit_card=None):
    customers = []
    for i in range(100):
        cust = get_mock_customer_profile(10000 + i)
        customers.append(cust)
    df = pd.DataFrame(customers)
    
    # Filter
    if rfm_segment:
        df = df[df["rfm_segment"] == rfm_segment]
    if aum_bucket:
        df = df[df["aum_bucket"] == aum_bucket]
    if has_credit_card is not None:
        df = df[df["has_credit_card"] == has_credit_card]
        
    return df[[
        "customer_id", "full_name_masked", "age", "gender", 
        "customer_segment", "aum_bucket", "rfm_segment", 
        "aum_million_vnd", "has_credit_card", "churn_flag"
    ]]

def get_mock_cohort_retention(segment=None, aum_bucket=None):
    months = [f"2025-{i:02d}" for i in range(1, 13)]
    records = []
    
    # Tạo đường cong suy giảm retention mặc định
    # VIP giữ chân tốt nhất, MASS giữ chân kém nhất
    base_decay = [100.0, 75.0, 68.0, 62.0, 58.0, 55.0, 52.0, 50.0, 48.0, 47.0, 45.0, 44.0]
    if segment == "VIP" or aum_bucket == "VIP":
        base_decay = [100.0, 92.0, 89.0, 87.0, 85.0, 84.0, 83.0, 82.0, 82.0, 81.0, 80.0, 80.0]
    elif segment == "PRIORITY" or aum_bucket == "PRIORITY":
        base_decay = [100.0, 85.0, 80.0, 76.0, 74.0, 72.0, 70.0, 69.0, 68.0, 67.0, 66.0, 65.0]
    elif segment == "RETAIL" or aum_bucket == "MASS":
        base_decay = [100.0, 68.0, 58.0, 52.0, 47.0, 43.0, 40.0, 38.0, 36.0, 34.0, 32.0, 30.0]
        
    np.random.seed(42)
    for i, start_month in enumerate(months):
        cohort_size = int(np.random.randint(400, 1000))
        if segment == "VIP" or aum_bucket == "VIP":
            cohort_size = int(np.random.randint(30, 80))
        elif segment == "PRIORITY" or aum_bucket == "PRIORITY":
            cohort_size = int(np.random.randint(100, 250))
            
        for period in range(12 - i):
            noise = np.random.normal(0, 1.5)
            rate = max(0.0, min(100.0, base_decay[period] + noise))
            if period == 0:
                rate = 100.0
            
            active_cust = int(round(cohort_size * rate / 100.0))
            records.append({
                "cohort_month": start_month,
                "cohort_size": cohort_size,
                "period": f"M{period}",
                "active_customers": active_cust,
                "retention_rate": round(rate, 1)
            })
            
    return pd.DataFrame(records)


# =============================================================================
# Mock data bổ sung cho Trang 1 (EDA), Trang 2 (RFM & Địa lý), Trang 5 (Ops Health)
# =============================================================================

def get_mock_eda_kpis():
    return {
        "total_customers": 10000,
        "avg_age": 38.4,
        "pct_kyc_verified": 91.2,
        "pct_new_this_month": 3.1,
    }


def get_mock_gender_distribution():
    data = {
        "gender": ["M", "F"],
        "customer_count": [5150, 4850],
    }
    return pd.DataFrame(data)


def get_mock_age_distribution():
    data = {
        "age_bucket": ["<25", "25-34", "35-44", "45-54", "55-64", "65+"],
        "customer_count": [900, 2800, 2900, 1800, 1100, 500],
    }
    return pd.DataFrame(data)


def get_mock_kyc_distribution():
    data = {
        "kyc_status": ["VERIFIED", "PENDING"],
        "customer_count": [9120, 880],
    }
    return pd.DataFrame(data)


def get_mock_register_trend():
    months = [f"2023-{i:02d}" for i in range(1, 13)] + [f"2024-{i:02d}" for i in range(1, 13)] + [f"2025-{i:02d}" for i in range(1, 13)]
    np.random.seed(7)
    base = np.linspace(180, 420, len(months))
    noise = np.random.normal(0, 25, len(months))
    counts = np.clip(base + noise, 50, None).astype(int)
    return pd.DataFrame({"reg_month": months, "customer_count": counts})


def get_mock_geo_city_distribution():
    # Dùng thẳng cột city thật (chỉ 3 giá trị cố định trong data nguồn — xem
    # geo_utils.CITY_NAME_MAP để biết lý do) thay vì suy diễn qua branch_code.
    data = {
        "city": ["Ha Noi", "Ho Chi Minh", "Da Nang"],
        "customer_count": [3350, 3300, 3350],
        "total_aum_billion": [1150.0, 1650.0, 656.28],
    }
    return pd.DataFrame(data)


def get_mock_geo_distribution():
    # Prefix khớp với dashboard/geo_utils.py PROVINCE_MAP (HCM, HAN, DAN, HPG, BDG,
    # KHH, HUE, QNI, NAN, DNI, CTH, NDH) để bản đồ giả lập hiển thị đúng khi offline.
    data = {
        "primary_branch_code": [
            "HCM001", "HCM005", "HAN002", "HAN008", "DAN003", "HPG002",
            "BDG001", "KHH002", "HUE001", "QNI001", "NAN001", "DNI001", "CTH001", "NDH001",
        ],
        "customer_count": [1450, 950, 1200, 800, 900, 700, 650, 500, 450, 380, 350, 420, 400, 200],
        "total_aum_billion": [520.4, 310.2, 480.1, 260.5, 300.4, 210.1, 195.3, 150.2, 130.5, 100.4, 90.2, 140.5, 120.1, 55.3],
    }
    return pd.DataFrame(data)


def get_mock_ops_health():
    import datetime
    jobs = [
        ("bronze_initial_dag", "bronze", "core_customer"),
        ("bronze_core_banking_dag", "bronze", "core_account"),
        ("bronze_card_crm_dag", "bronze", "crm_interaction"),
        ("silver_all_dag", "silver", "dim_customer"),
        ("silver_all_dag", "silver", "fact_txn_account"),
        ("silver_all_dag", "silver", "fact_card_txn"),
        ("gold_segmentation_dag", "gold", "rfm_segment"),
        ("gold_segmentation_dag", "gold", "churn_prediction"),
        ("gold_segmentation_dag", "gold", "cross_sell_segment"),
        ("gold_segmentation_dag", "gold", "campaign_target"),
        ("gold_mart360_dag", "gold", "mart_customer_360"),
        ("gold_time_analytics_dag", "gold", "mart_branch_monthly_summary"),
        ("ops_pii_masking_daily_dag", "sandbox", "mart_customer_360_masked"),
    ]
    cob_dt = "2025-12-31"
    base = datetime.datetime(2026, 1, 2, 4, 30, 0)
    records = []
    for i, (job, schema, table) in enumerate(jobs):
        start = base + datetime.timedelta(minutes=i * 7)
        duration = np.random.randint(2, 15)
        status = "S" if i != len(jobs) - 2 else "R"  # 1 job giả lập đang chạy dở
        end = start + datetime.timedelta(minutes=duration) if status == "S" else None
        records.append({
            "job_name": job,
            "schema_name": schema,
            "table_name": table,
            "cob_dt": cob_dt,
            "start_time": start,
            "end_time": end,
            "latest_status": status,
            "duration_minutes": duration if status == "S" else None,
        })
    return pd.DataFrame(records)
