from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recoveriq.config import DB_PATH, EXPECTED_FILES, KAGGLE_URL, RANDOM_STATE, RAW_DIR


def _missing_files() -> list[str]:
    return [name for name in EXPECTED_FILES.values() if not (RAW_DIR / name).exists()]


def download_olist(force: bool = False) -> dict[str, str]:
    """Download and safely extract the public Olist archive."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and not _missing_files():
        return {"status": "already_present", "directory": str(RAW_DIR)}

    with tempfile.TemporaryDirectory(prefix="recoveriq-") as tmp:
        archive = Path(tmp) / "olist.zip"
        request = urllib.request.Request(KAGGLE_URL, headers={"User-Agent": "RecoverIQ/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as out:
            shutil.copyfileobj(response, out)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                target = (RAW_DIR / Path(member.filename).name).resolve()
                if RAW_DIR.resolve() not in target.parents or member.is_dir():
                    continue
                if target.name in EXPECTED_FILES.values():
                    with zf.open(member) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)

    missing = _missing_files()
    if missing:
        raise RuntimeError(f"Olist archive did not contain expected files: {missing}")
    manifest = {"source": KAGGLE_URL, "archive_sha256": digest, "files": EXPECTED_FILES}
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"status": "downloaded", "sha256": digest, "directory": str(RAW_DIR)}


def generate_demo_data(rows: int = 2500, force: bool = False) -> dict[str, str | int]:
    """Generate structurally realistic data for tests, never for portfolio claims."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and not _missing_files():
        raise FileExistsError("Raw data exists. Pass --force to replace it with demo data.")
    rng = np.random.default_rng(RANDOM_STATE)
    n_customers, n_sellers, n_products = max(200, rows // 4), 60, 180
    states = np.array(["SP", "RJ", "MG", "PR", "RS", "BA", "SC", "GO"])
    categories = np.array(["health_beauty", "computers", "home_decor", "sports", "books"])

    unique_customers = np.array([f"cu_{i:05d}" for i in range(n_customers)])
    popularity = rng.pareto(3, n_customers) + 0.15
    customer_unique = rng.choice(unique_customers, rows, p=popularity / popularity.sum())
    customer_ids = np.array([f"c_{i:06d}" for i in range(rows)])
    customer_state = rng.choice(states, rows, p=[0.36, 0.16, 0.14, 0.09, 0.08, 0.07, 0.06, 0.04])
    state_zip = {state: 10000 + i * 1000 for i, state in enumerate(states)}
    customer_zip = np.array([state_zip[s] + int(rng.integers(0, 100)) for s in customer_state])
    customers = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "customer_unique_id": customer_unique,
            "customer_zip_code_prefix": customer_zip,
            "customer_city": [f"city_{s.lower()}" for s in customer_state],
            "customer_state": customer_state,
        }
    )

    seller_ids = np.array([f"s_{i:04d}" for i in range(n_sellers)])
    seller_state = rng.choice(states, n_sellers)
    seller_zip = np.array([state_zip[s] + int(rng.integers(0, 100)) for s in seller_state])
    sellers = pd.DataFrame(
        {
            "seller_id": seller_ids,
            "seller_zip_code_prefix": seller_zip,
            "seller_city": [f"city_{s.lower()}" for s in seller_state],
            "seller_state": seller_state,
        }
    )
    seller_delay = dict(zip(seller_ids, rng.normal(0, 2.2, n_sellers), strict=True))

    product_ids = np.array([f"p_{i:05d}" for i in range(n_products)])
    product_categories = rng.choice(categories, n_products)
    products = pd.DataFrame(
        {
            "product_id": product_ids,
            "product_category_name": product_categories,
            "product_name_lenght": rng.integers(20, 70, n_products),
            "product_description_lenght": rng.integers(100, 1200, n_products),
            "product_photos_qty": rng.integers(1, 8, n_products),
            "product_weight_g": rng.integers(100, 8000, n_products),
            "product_length_cm": rng.integers(10, 90, n_products),
            "product_height_cm": rng.integers(2, 60, n_products),
            "product_width_cm": rng.integers(8, 70, n_products),
        }
    )

    order_ids = np.array([f"o_{i:06d}" for i in range(rows)])
    purchase = pd.Timestamp("2017-01-01") + pd.to_timedelta(np.sort(rng.integers(0, 570, rows)), unit="D")
    purchase = purchase + pd.to_timedelta(rng.integers(0, 24, rows), unit="h")
    approval = purchase + pd.to_timedelta(rng.integers(1, 18, rows), unit="h")
    promised_days = rng.integers(8, 25, rows)
    selected_sellers = rng.choice(seller_ids, rows)
    same_state = customer_state == np.array([seller_state[int(s[2:])] for s in selected_sellers])
    actual_days = np.maximum(
        2,
        np.round(
            rng.normal(9, 3.5, rows)
            + np.where(same_state, -2, 3)
            + np.array([seller_delay[s] for s in selected_sellers])
        ),
    ).astype(int)
    delivered = approval + pd.to_timedelta(actual_days, unit="D")
    estimated = approval.normalize() + pd.to_timedelta(promised_days, unit="D")
    cancelled = rng.random(rows) < 0.018
    status = np.where(cancelled, "canceled", "delivered")
    carrier = approval + pd.to_timedelta(rng.integers(1, 5, rows), unit="D")
    orders = pd.DataFrame(
        {
            "order_id": order_ids,
            "customer_id": customer_ids,
            "order_status": status,
            "order_purchase_timestamp": purchase,
            "order_approved_at": approval,
            "order_delivered_carrier_date": carrier.where(~cancelled, pd.NaT),
            "order_delivered_customer_date": delivered.where(~cancelled, pd.NaT),
            "order_estimated_delivery_date": estimated,
        }
    )

    item_rows, payment_rows = [], []
    order_value = np.zeros(rows)
    primary_category = []
    for i, order_id in enumerate(order_ids):
        count = int(rng.choice([1, 2, 3], p=[0.83, 0.14, 0.03]))
        chosen = rng.choice(product_ids, count)
        primary_category.append(product_categories[int(chosen[0][2:])])
        for item_no, product_id in enumerate(chosen, 1):
            price = float(np.round(rng.lognormal(4.2, 0.7), 2))
            freight = float(np.round(price * rng.uniform(0.08, 0.28), 2))
            order_value[i] += price + freight
            item_rows.append(
                {
                    "order_id": order_id,
                    "order_item_id": item_no,
                    "product_id": product_id,
                    "seller_id": selected_sellers[i],
                    "shipping_limit_date": approval[i] + pd.Timedelta(days=5),
                    "price": price,
                    "freight_value": freight,
                }
            )
        payment_rows.append(
            {
                "order_id": order_id,
                "payment_sequential": 1,
                "payment_type": rng.choice(["credit_card", "boleto", "voucher"]),
                "payment_installments": int(rng.integers(1, 8)),
                "payment_value": round(order_value[i], 2),
            }
        )

    late = delivered.normalize() > estimated
    low_probability = np.clip(0.08 + 0.55 * late.astype(float) + 0.04 * (order_value > 250), 0, 0.9)
    low_review = rng.random(rows) < low_probability
    review_score = np.where(low_review, rng.integers(1, 3, rows), rng.integers(3, 6, rows))
    reviews = pd.DataFrame(
        {
            "review_id": [f"r_{i:06d}" for i in range(rows)],
            "order_id": order_ids,
            "review_score": review_score,
            "review_comment_title": "",
            "review_comment_message": "",
            "review_creation_date": delivered + pd.Timedelta(days=1),
            "review_answer_timestamp": delivered + pd.Timedelta(days=2),
        }
    )

    geo_rows = []
    state_centres = {s: (-23 + i * 1.2, -47 + i * 0.8) for i, s in enumerate(states)}
    for state, base_zip in state_zip.items():
        for offset in range(100):
            lat, lng = state_centres[state]
            geo_rows.append(
                {
                    "geolocation_zip_code_prefix": base_zip + offset,
                    "geolocation_lat": lat + rng.normal(0, 0.15),
                    "geolocation_lng": lng + rng.normal(0, 0.15),
                    "geolocation_city": f"city_{state.lower()}",
                    "geolocation_state": state,
                }
            )

    outputs = {
        "customers": customers,
        "geolocation": pd.DataFrame(geo_rows),
        "order_items": pd.DataFrame(item_rows),
        "order_payments": pd.DataFrame(payment_rows),
        "order_reviews": reviews,
        "orders": orders,
        "products": products,
        "sellers": sellers,
        "category_translation": pd.DataFrame(
            {
                "product_category_name": categories,
                "product_category_name_english": [c.replace("_", " ") for c in categories],
            }
        ),
    }
    for key, frame in outputs.items():
        frame.to_csv(RAW_DIR / EXPECTED_FILES[key], index=False)
    manifest = {
        "source": "synthetic_demo",
        "warning": "Engineering verification only. Do not use these results in portfolio claims.",
        "seed": RANDOM_STATE,
        "rows": rows,
    }
    (RAW_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"status": "generated", "rows": rows, "directory": str(RAW_DIR)}


def ingest_raw() -> dict[str, int]:
    missing = _missing_files()
    if missing:
        raise FileNotFoundError(f"Missing raw files: {missing}. Run download or demo-data first.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with duckdb.connect(str(DB_PATH)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        for table, filename in EXPECTED_FILES.items():
            path = (RAW_DIR / filename).as_posix().replace("'", "''")
            con.execute(
                f"CREATE OR REPLACE TABLE raw.{table} AS "
                f"SELECT * FROM read_csv_auto('{path}', header=true, sample_size=-1)"
            )
            counts[table] = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
    return counts
