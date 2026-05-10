"""
Prediction module for CryptoBot ML.

Usage:
    python -m src.models.predict_model BTCUSDT
    python -m src.models.predict_model          # defaults to BTCUSDT
"""
import argparse
import logging
import pickle
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("CRYPTO_BOT")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

SAVED_DIR = Path(__file__).parent.parent.parent / "models" / "saved"
SIGNAL_NAMES: Dict[int, str] = {1: "BUY", 0: "HOLD", -1: "SELL"}

# Fallback spreads (USD) used when Binance is unreachable within the timeout.
_FALLBACK_SPREADS: Dict[str, float] = {
    "BTCUSDT": 2.0,
    "ETHUSDT": 0.5,
    "SOLUSDT": 0.1,
}


def calculate_profitability_filter(
    symbol: str, confidence: float, signal: int, price: float
) -> Dict:
    """
    Fetch bid/ask from Binance via ccxt, compute profitability threshold,
    and override signal to HOLD if expected movement < threshold.

    threshold = (spread + binance_fees_0.1pct) × 10
    expected_movement = confidence × price

    Returns: {signal, spread, profitability_threshold}
    Network call has a 3-second timeout; on failure uses a fixed fallback spread
    so the prediction is never blocked.
    """
    try:
        import ccxt

        try:
            exchange = ccxt.binance({"timeout": 3000})
            ticker = exchange.fetch_ticker(symbol)
            bid = float(ticker.get("bid") or 0.0)
            ask = float(ticker.get("ask") or 0.0)
            spread = ask - bid
            spread_source = "live"
        except Exception as net_err:
            spread = _FALLBACK_SPREADS.get(symbol, 1.0)
            spread_source = "fallback"
            logger.warning(
                f"[{symbol}] Binance ticker unavailable ({net_err}); "
                f"using fallback spread={spread}"
            )

        fees = price * 0.001  # 0.1% Binance maker/taker
        threshold = (spread + fees) * 10
        expected_movement = confidence * price

        filtered_signal = signal
        if signal != 0 and expected_movement < threshold:
            filtered_signal = 0
            logger.info(
                f"[{symbol}] Profitability filter → HOLD "
                f"(expected={expected_movement:.4f} < threshold={threshold:.4f}, "
                f"spread={spread:.6f} [{spread_source}])"
            )

        return {
            "signal": filtered_signal,
            "spread": round(spread, 6),
            "profitability_threshold": round(threshold, 6),
        }
    except Exception as e:
        logger.warning(f"[{symbol}] Profitability filter unavailable: {e}")
        return {"signal": signal, "spread": None, "profitability_threshold": None}


def load_model(symbol: str) -> tuple:
    """Load (model, metrics) from models/saved/<symbol>/model.pkl."""
    path = SAVED_DIR / symbol / "model.pkl"
    if not path.exists():
        raise FileNotFoundError(
            f"No model for {symbol} at {path}. Run train_model first."
        )
    with open(path, "rb") as f:
        bundle = pickle.load(f)
    return bundle["model"], bundle["metrics"]


def get_latest_features(symbol: str, feature_cols: list) -> pd.DataFrame:
    """Fetch the most recent feature row for a symbol from PostgreSQL."""
    from src.data.config import SETTINGS
    from src.data.connector.connector import connect_to_postgres

    engine = connect_to_postgres(
        db_name=SETTINGS["POSTGRES_DB"],
        user=SETTINGS["POSTGRES_USER"],
        password=SETTINGS["POSTGRES_PASSWORD"],
        host=SETTINGS["DB_HOST"],
        port=int(SETTINGS["POSTGRES_PORT"]),
    )
    # "close" is already in feature_cols; only add "timestamp" for display
    extra = ['"timestamp"']
    cols_sql = ", ".join([f'"{c}"' for c in feature_cols] + extra)
    query = (
        f"SELECT {cols_sql} FROM features "
        f"WHERE symbol = '{symbol}' ORDER BY timestamp DESC LIMIT 1"
    )
    df = pd.read_sql(query, engine)
    engine.dispose()
    return df


def predict(symbol: str) -> Dict:
    """
    Generate a BUY / SELL / HOLD signal for the latest candle of a symbol.

    Returns a dict with keys:
      symbol, signal, signal_label, confidence, price, timestamp, model_version.
    """
    model, metrics = load_model(symbol)
    feature_cols: list = metrics["feature_cols"]
    label_inv: Dict = {int(k): int(v) for k, v in metrics["label_inv"].items()}

    df = get_latest_features(symbol, feature_cols)
    if df.empty:
        raise ValueError(f"No feature rows found in DB for {symbol}")

    # Keep as DataFrame so LightGBM models receive named features (avoids sklearn warning)
    X = df[feature_cols]
    proba = model.predict_proba(X)[0]           # shape (3,): p(class_0), p(class_1), p(class_2)
    pred_idx = int(np.argmax(proba))
    confidence = float(proba[pred_idx])

    # label_inv maps model class index → original signal (-1 / 0 / 1)
    signal = label_inv[pred_idx]
    price = float(df["close"].iloc[0])

    # Apply profitability filter (spread + fees check)
    pf = calculate_profitability_filter(symbol, confidence, signal, price)
    signal = pf["signal"]

    return {
        "symbol": symbol,
        "signal": signal,
        "signal_label": SIGNAL_NAMES[signal],
        "confidence": round(confidence, 4),
        "price": price,
        "timestamp": str(df["timestamp"].iloc[0]),
        "model_version": metrics["model_version"],
        "spread": pf["spread"],
        "profitability_threshold": pf["profitability_threshold"],
    }


def predict_demo(symbol: str) -> dict:
    """Generate a prediction from mock features (no DB required — for testing)."""
    model, metrics = load_model(symbol)
    feature_cols: list = metrics["feature_cols"]
    label_inv: dict = {int(k): int(v) for k, v in metrics["label_inv"].items()}

    rng = np.random.default_rng(seed=42)
    mock_values = rng.uniform(low=0.01, high=1.0, size=(1, len(feature_cols)))
    # Set close to a realistic BTC price range
    close_idx = feature_cols.index("close") if "close" in feature_cols else 3
    mock_values[0, close_idx] = 93_000.0
    X = pd.DataFrame(mock_values, columns=feature_cols)

    proba = model.predict_proba(X)[0]
    pred_idx = int(np.argmax(proba))
    confidence = float(proba[pred_idx])
    signal = label_inv[pred_idx]

    return {
        "symbol": symbol,
        "signal": signal,
        "signal_label": SIGNAL_NAMES[signal],
        "confidence": round(confidence, 4),
        "price": float(X["close"].iloc[0]),
        "timestamp": "DEMO (no DB)",
        "model_version": metrics["model_version"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict BUY/SELL/HOLD for a symbol")
    parser.add_argument("symbol", nargs="?", default="BTCUSDT")
    parser.add_argument("--demo", action="store_true",
                        help="Run with mock features (no DB required)")
    args = parser.parse_args()

    result = predict_demo(args.symbol) if args.demo else predict(args.symbol)
    width = 42
    print(f"\n{'='*width}")
    print(f"  Symbol    : {result['symbol']}")
    print(f"  Price     : {result['price']:>12,.2f} USDT")
    print(f"  Signal    : {result['signal_label']}  ({result['signal']:+d})")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Timestamp : {result['timestamp']}")
    print(f"  Model     : {result['model_version']}")
    print(f"{'='*width}\n")
