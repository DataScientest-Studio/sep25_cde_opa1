from src.data.historical_data import get_historical_data
from datetime import datetime
import pandas as pd

df = get_historical_data(symbol="BTCUSDT",
                          start_time=datetime(2024, 4, 1), interval="1h",
                          end_time=datetime(2026, 4, 20))


df1 = df.copy()

'''on créé une colonne qui indique la variation en pourcentage d'une bougie (possible de tester avec high et low aussi)'''
df1.loc[:,'CandleVariation'] = (df['close']- df['open'])/df['open']

''' idem pour le volume, variation de volume,'''
df1.loc[:,'VolumeChange'] = df['volume'].pct_change()

'''La variation future'''
df1['target'] = df1['CandleVariation'].shift(-1)
'''Nombre d'observation dans le temps'''
n = 24

"créé n colonne pour n features, soit n variations de prix précédentes qui expliqueront le prix suivant "
for i in range(1, n+1):
        df1[f'variation_lag_{i}'] = df1['CandleVariation'].shift(i)
        df1[f'Volume_lag_{i}'] = df1['VolumeChange'].shift(i) # Après test d'importance des features pas significatif

df1 = df1.dropna()

'''with pd.option_context('display.max_columns', None, 'display.width', None):
    print(df1.head())'''

'''On sépare l'échantillon d'entrainement et de test de manière chronologique, sinon possible "leak" 
car en cas de random, certaines données à prédire se retrouverais dans les données laggé d'entrainement ou inversement'''

split_index = int(len(df1) * 0.8)
train = df1.iloc[:split_index]
test= df1.iloc[split_index:]

'''On ne garde que les variations laggé '''

X_train = train.drop([
    'open_time', 'open', 'high', 'low', 'close', 'volume',
    'close_time', 'quote_asset_volume', 'number_of_trades',
    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
    'ignore', 'target'], axis=1)

X_test = test.drop([
    'open_time', 'open', 'high', 'low', 'close', 'volume',
    'close_time', 'quote_asset_volume', 'number_of_trades',
    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
    'ignore', 'target'], axis=1)

y_train = train['target']

y_test = test['target']

from sklearn.ensemble import RandomForestRegressor

regressor = RandomForestRegressor(n_estimators=200, max_depth=6, min_samples_leaf=20, random_state=42, n_jobs=-1)

regressor.fit(X_train, y_train)


'''Score R², signe et magnitude du move'''
print(regressor.score(X_train,y_train))
print(regressor.score(X_test,y_test))

import numpy as np

y_pred = regressor.predict(X_test)

'''% du temps ou le signe est correct, juste la direction = hausse ou baisse'''
direction_correct = np.mean(np.sign(y_pred) == np.sign(y_test))
print(f"Directional accuracy : {direction_correct:.2%}")


from scipy.stats import binomtest

n_correct = np.sum(np.sign(y_pred) == np.sign(y_test))
n_total = len(y_test)

result = binomtest(n_correct, n_total, p=0.5, alternative='greater')
print(f"Bonnes prédictions : {n_correct}/{n_total}")
print(f"p-value : {result.pvalue:.4f}")


import pandas as pd

imp = pd.Series(regressor.feature_importances_, index=X_train.columns)
imp = imp.sort_values(ascending=False)

print("Top 10 features :")
print(imp.head(10).round(4))
print("\nBottom 10 features :")
print(imp.tail(10).round(4))
print(f"\nTotal features : {len(imp)}")