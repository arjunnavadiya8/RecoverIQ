from fastapi.testclient import TestClient

from recoveriq.api import app

client = TestClient(app)


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


def test_prediction_schema_rejects_post_outcome_or_invalid_values():
    response = client.post(
        "/predict",
        json={
            "price": -1,
            "freight_value": 10,
            "item_count": 1,
            "estimated_delivery_days": 10,
            "purchase_hour": 12,
            "purchase_day_of_week": 2,
            "purchase_month": 5,
            "customer_state": "SP",
            "seller_state": "RJ",
            "product_category_name_english": "books",
            "actual_delivery_days": 11,
        },
    )
    assert response.status_code == 422


def test_prediction_success_contract(monkeypatch):
    from recoveriq import api

    class FakeBundle:
        threshold = 0.2
        model_version = "test"

        @staticmethod
        def predict_proba(frame):
            return [0.35]

    monkeypatch.setattr(api, "get_bundle", lambda: FakeBundle())
    monkeypatch.setattr(
        api,
        "local_contributions",
        lambda bundle, frame: [{"feature": "estimated_delivery_days", "contribution": 0.7}],
    )
    response = client.post(
        "/predict",
        json={
            "price": 100,
            "freight_value": 10,
            "item_count": 1,
            "seller_count": 1,
            "estimated_delivery_days": 10,
            "customer_seller_distance_km": 500,
            "seller_prior_orders": 20,
            "seller_prior_late_rate": 0.1,
            "purchase_hour": 12,
            "purchase_day_of_week": 2,
            "purchase_month": 5,
            "customer_state": "SP",
            "seller_state": "RJ",
            "product_category_name_english": "books",
        },
    )
    assert response.status_code == 200
    assert response.json()["late_delivery_probability"] == 0.35
    assert response.json()["risk_band"] == "medium"
