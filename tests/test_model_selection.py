from backend.src.ml.train_future_model import select_production_model


def test_select_production_model_prefers_lowest_mae():
    summary = [
        {"model": "random_forest", "mae": 7.1, "rmse": 18.9},
        {"model": "zone_dow_hour_mean", "mae": 6.4, "rmse": 16.0},
        {"model": "linear_regression", "mae": 7.0, "rmse": 16.4},
    ]

    assert select_production_model(summary) == "zone_dow_hour_mean"


def test_select_production_model_uses_rmse_as_tiebreaker():
    summary = [
        {"model": "model_a", "mae": 5.0, "rmse": 12.0},
        {"model": "model_b", "mae": 5.0, "rmse": 11.0},
    ]

    assert select_production_model(summary) == "model_b"
