from src.data.historical_data import get_historical_data
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

def train_model(n: int = 24):
    """
    Entraîne le modèle et retourne le modèle entraîné
    ainsi que les colonnes de features pour la prédiction.
    """
    df = get_historical_data(
        symbol="BTCUSDT",
        start_time=datetime(2024, 4, 1),
        interval="1h",
        end_time=datetime(2026, 4, 20)
    )

    df1 = df.copy()
    df1['CandleVariation'] = (df['close'] - df['open']) / df['open']
    df1['VolumeChange']    = df['volume'].pct_change()
    df1['target']          = df1['CandleVariation'].shift(-1)

    for i in range(1, n + 1):
        df1[f'variation_lag_{i}'] = df1['CandleVariation'].shift(i)
        df1[f'Volume_lag_{i}']    = df1['VolumeChange'].shift(i)

    df1 = df1.dropna()

    cols_to_drop = [
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
        'ignore', 'target', 'CandleVariation', 'VolumeChange'
    ]

    split_index = int(len(df1) * 0.8)
    train = df1.iloc[:split_index]
    test  = df1.iloc[split_index:]

    X_train = train.drop(cols_to_drop, axis=1)
    X_test  = test.drop(cols_to_drop, axis=1)
    y_train = train['target']
    y_test  = test['target']

    model = RandomForestRegressor(
        n_estimators=200, max_depth=6,
        min_samples_leaf=20, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Logs de performance
    print(f"R² train : {model.score(X_train, y_train):.4f}")
    print(f"R² test  : {model.score(X_test, y_test):.4f}")

    y_pred = model.predict(X_test)
    direction_correct = np.mean(np.sign(y_pred) == np.sign(y_test))
    print(f"Directional accuracy : {direction_correct:.2%}")

    # Retourne le modèle ET les colonnes dans le bon ordre
    return model, list(X_train.columns)


if __name__ == "__main__":
    model, feature_cols = train_model(n=24)
    print(f"Modèle prêt — {len(feature_cols)} features")