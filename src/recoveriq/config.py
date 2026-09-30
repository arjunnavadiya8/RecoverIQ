from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
WAREHOUSE_DIR = ROOT / "data" / "warehouse"
DB_PATH = WAREHOUSE_DIR / "recoveriq.duckdb"
ARTIFACT_DIR = ROOT / "artifacts"
REPORT_DIR = ROOT / "reports"

EXPECTED_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
RANDOM_STATE = 42
MODEL_VERSION = "0.1.0"

FEATURE_COLUMNS = [
    "price",
    "freight_value",
    "item_count",
    "seller_count",
    "estimated_delivery_days",
    "customer_seller_distance_km",
    "seller_prior_orders",
    "seller_prior_late_rate",
    "purchase_hour",
    "purchase_day_of_week",
    "purchase_month",
    "customer_state",
    "seller_state",
    "product_category_name_english",
]

NUMERIC_FEATURES = FEATURE_COLUMNS[:11]
CATEGORICAL_FEATURES = FEATURE_COLUMNS[11:]

