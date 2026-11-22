import json
from datetime import datetime, timezone
import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor
from app.core.config import get_settings
from app.ml.features import (
    DELAY_CATEGORICAL_FEATURES,
    DELAY_NUMERIC_FEATURES,
    engineer_delay_features,
    engineer_stockout_features,
)

settings = get_settings()

TRUSTED_XGB_TYPES = [
    "xgboost.core.Booster",
    "xgboost.sklearn.XGBClassifier",
    "xgboost.sklearn.XGBRegressor",
]


def _build_delay_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), DELAY_NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                DELAY_CATEGORICAL_FEATURES,
            ),
        ]
    )


def _generate_stockout_training_data(
    inv_mart: pd.DataFrame, suppliers_df: pd.DataFrame
) -> pd.DataFrame:
    """Membentuk dataset historis skenario simulasi inventori & keterlambatan untuk melatih model Stockout."""
    rng = np.random.default_rng(42)
    merged = inv_mart.merge(
        suppliers_df[["supplier_id", "contracted_lead_time_days"]],
        left_on="primary_supplier_id",
        right_on="supplier_id",
        how="left",
    )

    records = []
    for _, row in merged.iterrows():
        for _ in range(25):
            dos = float(np.clip(rng.uniform(1.5, 28.0), 1.0, 35.0))
            net_dos = round(dos * rng.uniform(0.70, 0.85), 2)
            safety_ratio = round(dos / 10.0, 3)
            delay_prob = float(np.clip(rng.beta(2.0, 3.0), 0.01, 0.99))
            pred_delay = round(delay_prob * rng.uniform(4.0, 16.0), 2)
            lead_time = float(row.get("contracted_lead_time_days", 14.0))

            effective_cover_gap = net_dos - (lead_time * 0.55 + pred_delay)
            noise = rng.normal(0, 0.8)
            is_stockout = int((effective_cover_gap + noise) < 0.0)

            records.append(
                {
                    "warehouse_code": row["warehouse_code"],
                    "criticality": row["criticality"],
                    "days_of_supply": round(dos, 2),
                    "net_days_of_supply": net_dos,
                    "safety_stock_ratio": safety_ratio,
                    "daily_burn_rate": float(row["daily_burn_rate"]),
                    "predicted_delay_days": pred_delay,
                    "delay_probability": round(delay_prob, 4),
                    "contracted_lead_time_days": lead_time,
                    "is_stockout": is_stockout,
                }
            )
    return pd.DataFrame(records)


def train_and_register_all() -> dict:
    """Melatih model XGBoost Delay & Stockout, mencatat ke MLflow SQLite Registry, dan menyimpan artefak lokal."""
    registry_dir = settings.models_registry_dir.resolve()
    registry_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = registry_dir / "mlartifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    mlflow_db_uri = f"sqlite:///{(registry_dir / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(mlflow_db_uri)

    experiment_name = "NexusCore-SupplyChain-Predictive-ML"
    exp = mlflow.get_experiment_by_name(experiment_name)
    if exp is None:
        mlflow.create_experiment(
            name=experiment_name,
            artifact_location=artifacts_dir.as_uri(),
        )
    mlflow.set_experiment(experiment_name)

    shipments_df = pd.read_parquet(
        settings.curated_data_dir / "shipments_enriched.parquet"
    )
    inv_mart_df = pd.read_parquet(
        settings.curated_data_dir / "inventory_risk_mart.parquet"
    )
    suppliers_df = pd.read_parquet(settings.cleaned_data_dir / "suppliers.parquet")

    X_delay = engineer_delay_features(shipments_df)
    y_delay_cls = shipments_df["is_delayed"].astype(int)
    y_delay_reg = shipments_df["delay_days"].astype(float)

    (
        X_train,
        X_test,
        y_cls_train,
        y_cls_test,
        y_reg_train,
        y_reg_test,
    ) = train_test_split(
        X_delay,
        y_delay_cls,
        y_delay_reg,
        test_size=0.20,
        random_state=42,
        stratify=y_delay_cls,
    )

    metrics_summary: dict[str, dict] = {}

    # ==========================================================================
    # 1. MODEL 1: SUPPLIER DELAY RISK CLASSIFIER (XGBoost)
    # ==========================================================================
    with mlflow.start_run(run_name="xgb-supplier-delay-classifier"):
        cls_params = {
            "n_estimators": 140,
            "max_depth": 4,
            "learning_rate": 0.06,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "random_state": 42,
            "eval_metric": "logloss",
        }
        delay_cls_pipeline = Pipeline(
            steps=[
                ("preprocessor", _build_delay_preprocessor()),
                ("model", XGBClassifier(**cls_params)),
            ]
        )
        delay_cls_pipeline.fit(X_train, y_cls_train)

        y_proba = delay_cls_pipeline.predict_proba(X_test)[:, 1]
        y_pred = (y_proba >= 0.50).astype(int)

        cls_metrics = {
            "pr_auc": round(float(average_precision_score(y_cls_test, y_proba)), 4),
            "roc_auc": round(float(roc_auc_score(y_cls_test, y_proba)), 4),
            "f1_score": round(float(f1_score(y_cls_test, y_pred)), 4),
            "precision": round(
                float(precision_score(y_cls_test, y_pred, zero_division=0)), 4
            ),
            "recall": round(
                float(recall_score(y_cls_test, y_pred, zero_division=0)), 4
            ),
        }
        mlflow.log_params(cls_params)
        mlflow.log_metrics(cls_metrics)
        mlflow.sklearn.log_model(
            sk_model=delay_cls_pipeline,
            name="model",
            registered_model_name="nexuscore-delay-classifier",
            skops_trusted_types=TRUSTED_XGB_TYPES,
        )
        joblib.dump(delay_cls_pipeline, registry_dir / "delay_classifier.joblib")
        metrics_summary["delay_classifier"] = cls_metrics

    # ==========================================================================
    # 2. MODEL 2: SUPPLIER DELAY DURATION REGRESSOR (XGBoost)
    # ==========================================================================
    with mlflow.start_run(run_name="xgb-supplier-delay-regressor"):
        reg_params = {
            "n_estimators": 140,
            "max_depth": 4,
            "learning_rate": 0.06,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "random_state": 42,
        }
        delay_reg_pipeline = Pipeline(
            steps=[
                ("preprocessor", _build_delay_preprocessor()),
                ("model", XGBRegressor(**reg_params)),
            ]
        )
        delay_reg_pipeline.fit(X_train, y_reg_train)

        y_reg_pred = np.maximum(0.0, delay_reg_pipeline.predict(X_test))
        reg_metrics = {
            "mae_days": round(float(mean_absolute_error(y_reg_test, y_reg_pred)), 4),
            "rmse_days": round(
                float(root_mean_squared_error(y_reg_test, y_reg_pred)), 4
            ),
            "r2_score": round(float(r2_score(y_reg_test, y_reg_pred)), 4),
        }
        mlflow.log_params(reg_params)
        mlflow.log_metrics(reg_metrics)
        mlflow.sklearn.log_model(
            sk_model=delay_reg_pipeline,
            name="model",
            registered_model_name="nexuscore-delay-regressor",
            skops_trusted_types=TRUSTED_XGB_TYPES,
        )
        joblib.dump(delay_reg_pipeline, registry_dir / "delay_regressor.joblib")
        metrics_summary["delay_regressor"] = reg_metrics

    # ==========================================================================
    # 3. MODEL 3: COMPONENT STOCKOUT RISK CLASSIFIER (XGBoost)
    # ==========================================================================
    stockout_raw = _generate_stockout_training_data(inv_mart_df, suppliers_df)
    X_stk = engineer_stockout_features(stockout_raw)
    y_stk = stockout_raw["is_stockout"].astype(int)

    Xs_train, Xs_test, ys_train, ys_test = train_test_split(
        X_stk, y_stk, test_size=0.20, random_state=42, stratify=y_stk
    )

    with mlflow.start_run(run_name="xgb-component-stockout-classifier"):
        stk_params = {
            "n_estimators": 120,
            "max_depth": 3,
            "learning_rate": 0.07,
            "subsample": 0.90,
            "random_state": 42,
            "eval_metric": "logloss",
        }
        stockout_pipeline = Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("model", XGBClassifier(**stk_params)),
            ]
        )
        stockout_pipeline.fit(Xs_train, ys_train)

        ys_proba = stockout_pipeline.predict_proba(Xs_test)[:, 1]
        ys_pred = (ys_proba >= 0.50).astype(int)
        stk_metrics = {
            "pr_auc": round(float(average_precision_score(ys_test, ys_proba)), 4),
            "roc_auc": round(float(roc_auc_score(ys_test, ys_proba)), 4),
            "f1_score": round(float(f1_score(ys_test, ys_pred)), 4),
        }
        mlflow.log_params(stk_params)
        mlflow.log_metrics(stk_metrics)
        mlflow.sklearn.log_model(
            sk_model=stockout_pipeline,
            name="model",
            registered_model_name="nexuscore-stockout-classifier",
            skops_trusted_types=TRUSTED_XGB_TYPES,
        )
        joblib.dump(stockout_pipeline, registry_dir / "stockout_classifier.joblib")
        metrics_summary["stockout_classifier"] = stk_metrics

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "mlflow_tracking_uri": mlflow_db_uri,
        "training_rows_shipments": len(shipments_df),
        "training_rows_stockout": len(stockout_raw),
        "metrics": metrics_summary,
    }
    with (registry_dir / "model_metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata


if __name__ == "__main__":
    result = train_and_register_all()
    print("=== Fase 4 Predictive ML & MLflow Registration Selesai ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
