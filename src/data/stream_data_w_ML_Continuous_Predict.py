import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
import threading
import time
from datetime import datetime, timedelta
from collections import deque

from src.data.historical_data import get_historical_data
from src.data.stream_data_w_ML import stream_trades, BinanceStreamClient
from src.models.Modele_classification import train_model

try:
    from .config import SETTINGS
except ImportError:
    from config import SETTINGS

# ── 1. ENTRAINEMENT ───────────────────────────────────────────────────
print("Entraînement du modèle en cours...")
model, feature_cols = train_model(n=24)
print("Modèle prêt")
N_LAGS = 24

# ── 2. BUFFER INITIAL ─────────────────────────────────────────────────
def init_buffer(symbol: str = "BTCUSDT", n: int = N_LAGS) -> deque:
    """Charge les N+5 dernières bougies H1 depuis Binance."""
    end   = datetime.now()
    start = end - timedelta(hours=n + 5)

    df = get_historical_data(symbol=symbol, interval="1h",
                             start_time=start, end_time=end)

    buffer = deque(maxlen=n + 5)
    for _, row in df.iterrows():
        buffer.append({
            "open":   row["open"],
            "close":  row["close"],
            "volume": row["volume"],
        })

    print(f"Buffer initialisé avec {len(buffer)} bougies")
    return buffer


# ── 3. CONSTRUCTION DES FEATURES ──────────────────────────────────────
def build_features(buffer: deque,
                   current_open: float = None,
                   current_close: float = None,
                   current_volume: float = None) -> pd.DataFrame:
    """
    Reproduit exactement les calculs faits à l'entraînement.
    Si current_* sont fournis, la dernière bougie est remplacée
    par la bougie en cours (partielle) pour la prédiction toutes les 10s.
    """
    df = pd.DataFrame(list(buffer))

    # Remplace la dernière ligne par la bougie en cours si fournie
    if current_close is not None:
        df.iloc[-1] = {
            "open":   current_open,
            "close":  current_close,
            "volume": current_volume,
        }

    df['CandleVariation'] = (df['close'] - df['open']) / df['open']
    df['VolumeChange']    = df['volume'].pct_change()

    for i in range(1, N_LAGS + 1):
        df[f'variation_lag_{i}'] = df['CandleVariation'].shift(i)
        df[f'Volume_lag_{i}']    = df['VolumeChange'].shift(i)

    df = df.dropna()

    if df.empty:
        raise ValueError("Buffer pas assez rempli")

    return df[feature_cols].iloc[[-1]]


# ── 4. VARIABLES BOUGIE EN COURS ──────────────────────────────────────
current_hour = None
last_open    = None
last_close   = None
last_volume  = 0.0
buffer       = init_buffer()


# ── 5. BOUCLE DE PREDICTION TOUTES LES 10 SECONDES ───────────────────
def predict_loop():
    """
    Prédit toutes les 10 secondes.
    Les lags 2 à 24 sont fixes (bougies fermées).
    Seul lag_1 évolue avec le dernier prix connu de la bougie en cours.
    """
    while True:
        time.sleep(10)

        if current_hour is None:
            continue

        try:
            features = build_features(
                buffer,
                current_open=last_open,
                current_close=last_close,
                current_volume=last_volume
            )
            prediction = model.predict(features)[0]
            direction  = "HAUSSE 📈" if prediction > 0 else "BAISSE 📉"
            print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Prédiction prochaine bougie : {prediction:.4%} → {direction}")
        except ValueError as e:
            print(f"Pas encore assez de données : {e}")


# ── 6. CALLBACK STREAM ────────────────────────────────────────────────
def on_trade(data):
    """
    Callback appelé à chaque trade streamé.
    Reconstruit les bougies H1 et met à jour le buffer à chaque fermeture.
    """
    global current_hour, last_open, last_close, last_volume

    if data["type"] != "trade":
        return

    trade_hour = data["timestamp"].replace(minute=0, second=0, microsecond=0)

    # ── Première bougie ──
    if current_hour is None:
        current_hour = trade_hour
        last_open    = data["price"]
        last_close   = data["price"]
        last_volume  = data["quantity"]
        return

    # ── Même heure : mise à jour bougie en cours ──
    if trade_hour == current_hour:
        last_close   = data["price"]
        last_volume += data["quantity"]
        return

    # ── Changement d'heure : bougie fermée ──
    print(f"\nBougie fermée [{current_hour}] "
          f"O:{last_open:.2f} C:{last_close:.2f} V:{last_volume:.4f}")

    # Ajout de la bougie fermée au buffer
    buffer.append({
        "open":   last_open,
        "close":  last_close,
        "volume": last_volume,
    })

    # Initialise la nouvelle bougie
    current_hour = trade_hour
    last_open    = data["price"]
    last_close   = data["price"]
    last_volume  = data["quantity"]


# ── 7. LANCEMENT ──────────────────────────────────────────────────────
if __name__ == "__main__":

    # Lance la boucle de prédiction en arrière-plan
    pred_thread = threading.Thread(target=predict_loop, daemon=True)
    pred_thread.start()
    print("Boucle de prédiction lancée (toutes les 10 secondes)")

    # Lance le stream
    print("Lancement du stream...")
    stream_trades(
        symbols=['BTCUSDT'],
        callback=on_trade
    )