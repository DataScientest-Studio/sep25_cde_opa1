"""
Training pipeline for CryptoBot ML — 1D timeframe, fed from PostgreSQL.

Évolution de Train_1D_ML.py : au lieu de refaire un appel Binance +
recalcul des indicateurs en mémoire, ce script charge directement les
features déjà calculées par le pipeline Airflow (fetch_and_store) dans
la table PostgreSQL `features` — mêmes indicateurs, même source de
vérité que celle utilisée en production, pas de duplication de calcul.

Usage:
    python scripts/Train_1D_ML2.py
    python scripts/Train_1D_ML2.py --symbol BTCUSDT
"""
import argparse
import json
import logging
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.utils.class_weight import compute_sample_weight
import xgboost as xgb
import lightgbm as lgb

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("RETRAIN_1D_PG")

SAVED_DIR = ROOT / "models" / "saved"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

LABEL_MAP: Dict[int, int] = {-1: 0, 0: 1, 1: 2}
LABEL_INV: Dict[int, int] = {0: -1, 1: 0, 2: 1}
SIGNAL_NAMES: Dict[int, str] = {-1: "SELL", 0: "HOLD", 1: "BUY"}

SPREAD_FALLBACK: Dict[str, float] = {"BTCUSDT": 2.0, "ETHUSDT": 0.5, "SOLUSDT": 0.1}
FEE_RATE = 0.001

FEATURE_COLS: List[str] = [
    "open", "high", "low", "close", "volume",
    "rsi_14", "macd", "macd_hist", "macd_signal",
    "bb_lower", "bb_mid", "bb_upper", "bb_bandwidth", "bb_percent",
    "ema_9", "ema_21", "ema_55",
    "sma_20", "sma_50", "sma_200",
    "atr_14",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "return_1h", "return_4h", "return_24h",
]


def _get_spread(symbol: str) -> float:
    try:
        import ccxt
        exchange = ccxt.binance()
        ob = exchange.fetch_order_book(symbol[:-4] + "/USDT", limit=1)
        return float(ob["asks"][0][0] - ob["bids"][0][0])
    except Exception:
        return SPREAD_FALLBACK.get(symbol, 1.0)


def load_features_from_postgres(symbol: str) -> pd.DataFrame:
    """Load all 1D feature rows for one symbol from the PostgreSQL `features` table.

    Same table/columns as src/models/train_model.py::load_features() —
    populated by the Airflow DAG fetch_and_store (interval="1d").
    """
    from sqlalchemy import text
    from src.data.config import SETTINGS
    from src.data.connector.connector import connect_to_postgres

    engine = connect_to_postgres(
        db_name=SETTINGS["POSTGRES_DB"],
        user=SETTINGS["POSTGRES_USER"],
        password=SETTINGS["POSTGRES_PASSWORD"],
        host=SETTINGS["DB_HOST"],
        port=int(SETTINGS["POSTGRES_PORT"]),
    )
    query = text(f"SELECT * FROM features WHERE symbol = '{symbol}' ORDER BY timestamp ASC")
    with engine.connect() as conn:
        result = conn.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    engine.dispose()
    return df


def make_target(close: pd.Series, spread: float) -> pd.Series:
    threshold_rate = (spread + close * FEE_RATE) / close + 0.01
    next_ret = close.shift(-1) / close - 1
    signal = pd.Series(0.0, index=close.index)
    signal[next_ret > threshold_rate] = 1.0
    signal[next_ret < -threshold_rate] = -1.0
    signal[next_ret.isna()] = np.nan
    return signal


def chronological_split(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    return (
        df.iloc[: int(n * 0.70)].copy(),
        df.iloc[int(n * 0.70): int(n * 0.85)].copy(),
        df.iloc[int(n * 0.85):].copy(),
    )


def compute_backtest_metrics(close: pd.Series, predictions: np.ndarray, spread: float) -> dict:
    actual = close.pct_change().shift(-1).fillna(0).values
    cost = np.where(predictions != 0, spread / close.values, 0.0)
    strat = np.where(predictions == 1,  actual - cost,
            np.where(predictions == -1, -actual - cost, 0.0))
    std = strat.std()
    sharpe = float(strat.mean() / std * np.sqrt(365)) if std != 0 else 0.0
    cumulative = np.cumsum(strat)
    return {
        "sharpe": sharpe,
        "pnl": float(strat.sum()),
        "max_drawdown": float(np.min(cumulative - np.maximum.accumulate(cumulative))) if len(cumulative) else 0.0,
    }


def _fit_xgboost(X_tr, y_tr, X_val, y_val, sw) -> xgb.XGBClassifier:
    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        objective="multi:softprob", num_class=3,
        eval_metric="mlogloss", early_stopping_rounds=30,
        random_state=42, verbosity=0,
    )
    model.fit(X_tr, y_tr, sample_weight=sw, eval_set=[(X_val, y_val)], verbose=False)
    return model


def _fit_lightgbm(X_tr, y_tr, X_val, y_val, sw) -> lgb.LGBMClassifier:
    model = lgb.LGBMClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        num_leaves=31, random_state=42, verbosity=-1,
    )
    model.fit(
        pd.DataFrame(X_tr, columns=FEATURE_COLS), y_tr,
        sample_weight=sw,
        eval_set=[(pd.DataFrame(X_val, columns=FEATURE_COLS), y_val)],
    )
    return model


def retrain_symbol(symbol: str) -> Tuple[object, Dict]:
    spread = _get_spread(symbol)
    logger.info(f"=== {symbol} — 1d features from PostgreSQL, spread={spread:.4f}  fee={FEE_RATE} ===")

    df = load_features_from_postgres(symbol)
    if df.empty:
        raise ValueError(f"No features in DB for {symbol}")

    df["target"] = make_target(df["close"], spread)
    df = df.dropna(subset=FEATURE_COLS + ["target"]).reset_index(drop=True)
    df["target"] = df["target"].astype(int)

    if len(df) < 100:
        raise ValueError(f"Not enough clean rows for {symbol}: {len(df)}")

    dist = dict(df["target"].value_counts().sort_index())
    logger.info(f"Dataset: {len(df)} rows — class dist: {dist}")

    train_df, val_df, test_df = chronological_split(df)
    logger.info(f"Split — train:{len(train_df)} val:{len(val_df)} test:{len(test_df)}")

    X_tr  = train_df[FEATURE_COLS].values
    y_tr  = np.array([LABEL_MAP[v] for v in train_df["target"]])
    X_val = val_df[FEATURE_COLS].values
    y_val = np.array([LABEL_MAP[v] for v in val_df["target"]])
    X_te  = test_df[FEATURE_COLS].values
    y_te  = np.array([LABEL_MAP[v] for v in test_df["target"]])
    sw    = compute_sample_weight("balanced", y_tr)

    test_close = test_df["close"].reset_index(drop=True)

    xgb_m    = _fit_xgboost(X_tr, y_tr, X_val, y_val, sw)
    xgb_pred = np.array([LABEL_INV[p] for p in xgb_m.predict(X_te)])
    y_orig   = np.array([LABEL_INV[p] for p in y_te])
    xgb_acc  = accuracy_score(y_orig, xgb_pred)
    xgb_f1   = f1_score(y_orig, xgb_pred, average="macro", zero_division=0)
    xgb_bt   = compute_backtest_metrics(test_close, xgb_pred, spread)
    logger.info(
        f"XGBoost  acc={xgb_acc:.3f} f1={xgb_f1:.3f} sharpe={xgb_bt['sharpe']:.3f} "
        f"pnl={xgb_bt['pnl']:.3f} dd={xgb_bt['max_drawdown']:.3f}"
    )

    lgb_m    = _fit_lightgbm(X_tr, y_tr, X_val, y_val, sw)
    lgb_pred = np.array([LABEL_INV[p] for p in lgb_m.predict(pd.DataFrame(X_te, columns=FEATURE_COLS))])
    lgb_acc  = accuracy_score(y_orig, lgb_pred)
    lgb_f1   = f1_score(y_orig, lgb_pred, average="macro", zero_division=0)
    lgb_bt   = compute_backtest_metrics(test_close, lgb_pred, spread)
    logger.info(
        f"LightGBM acc={lgb_acc:.3f} f1={lgb_f1:.3f} sharpe={lgb_bt['sharpe']:.3f} "
        f"pnl={lgb_bt['pnl']:.3f} dd={lgb_bt['max_drawdown']:.3f}"
    )

    if xgb_f1 >= lgb_f1:
        best_name, best_model = "xgboost", xgb_m
        best_acc, best_f1 = xgb_acc, xgb_f1
        best_sharpe, best_pnl, best_drawdown = xgb_bt["sharpe"], xgb_bt["pnl"], xgb_bt["max_drawdown"]
    else:
        best_name, best_model = "lightgbm", lgb_m
        best_acc, best_f1 = lgb_acc, lgb_f1
        best_sharpe, best_pnl, best_drawdown = lgb_bt["sharpe"], lgb_bt["pnl"], lgb_bt["max_drawdown"]

    logger.info(f"Winner: {best_name}  f1={best_f1:.3f}  sharpe={best_sharpe:.3f}")

    version = f"{symbol}_1d_{best_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    metrics = {
        "symbol":         symbol,
        "timeframe":      "1d",
        "data_source":    "postgresql:features",
        "model_name":     best_name,
        "model_version":  version,
        "date_train":     datetime.now(timezone.utc).isoformat(),
        "n_train":        len(train_df),
        "n_val":          len(val_df),
        "n_test":         len(test_df),
        "accuracy":       round(best_acc, 4),
        "f1_macro":       round(best_f1, 4),
        "sharpe_ratio":   round(best_sharpe, 4),
        "pnl":            round(best_pnl, 4),
        "max_drawdown":   round(best_drawdown, 4),
        "threshold_type": "dynamic",
        "spread_used":    round(spread, 4),
        "fee_rate":       FEE_RATE,
        "feature_cols":   FEATURE_COLS,
        "label_map":      LABEL_MAP,
        "label_inv":      LABEL_INV,
        "all_models": {
            "xgboost":  {"accuracy": round(xgb_acc, 4), "f1_macro": round(xgb_f1, 4), "sharpe": round(xgb_bt["sharpe"], 4), "pnl": round(xgb_bt["pnl"], 4), "max_drawdown": round(xgb_bt["max_drawdown"], 4)},
            "lightgbm": {"accuracy": round(lgb_acc, 4), "f1_macro": round(lgb_f1, 4), "sharpe": round(lgb_bt["sharpe"], 4), "pnl": round(lgb_bt["pnl"], 4), "max_drawdown": round(lgb_bt["max_drawdown"], 4)},
        },
    }
    return best_model, metrics


def save_model(model: object, metrics: Dict, symbol: str) -> Path:
    save_dir = SAVED_DIR / f"{symbol}_1d"
    save_dir.mkdir(parents=True, exist_ok=True)
    pkl_path = save_dir / "model.pkl"
    with open(pkl_path, "wb") as f:
        pickle.dump({"model": model, "metrics": metrics}, f)
    json_path = save_dir / "metrics.json"
    with open(json_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    logger.info(f"Saved → {pkl_path}")
    return save_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retrain CryptoBot on 1d data sourced from PostgreSQL features table")
    parser.add_argument("--symbol", default=None, help="Single symbol (default: all)")
    args = parser.parse_args()

    targets = [args.symbol.upper()] if args.symbol else SYMBOLS
    for sym in targets:
        try:
            model, metrics = retrain_symbol(sym)
            save_model(model, metrics, sym)
            test_days = metrics["n_test"]
            pnl_annual = metrics["pnl"] * (365 / test_days) if test_days else 0.0
            print(
                f"\n{sym}: acc={metrics['accuracy']}  "
                f"f1={metrics['f1_macro']}  sharpe={metrics['sharpe_ratio']}  "
                f"pnl_annual={pnl_annual * 100:.2f}%  dd={metrics['max_drawdown'] * 100:.2f}%"
            )
        except Exception as exc:
            logger.error(f"{sym}: training failed — {exc}")
