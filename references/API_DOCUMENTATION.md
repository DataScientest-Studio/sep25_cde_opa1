# API Documentation

## Vue d'ensemble

Cette API REST permet d'interroger les données historiques de cryptomonnaies stockées dans MongoDB.

## Démarrage

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Configuration

Assurez-vous que votre fichier `.env` contient les variables suivantes :

```env
MONGO_DB=crypto_db
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=your_user
MONGO_PASSWORD=your_password
```

### Lancer l'API

```bash
python run_api.py
```

L'API sera accessible sur `http://localhost:8000`

## Endpoints disponibles

### 1. Health Check

**GET** `/health`

Vérifie que l'API et la base de données sont opérationnelles.

**Exemple de réponse :**
```json
{
  "status": "healthy",
  "message": "All services are operational"
}
```

---

### 2. Liste des symboles disponibles

**GET** `/api/symbols`

Retourne la liste de tous les symboles de cryptomonnaies disponibles.

**Exemple de réponse :**
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
}
```

---

### 3. Liste des intervalles disponibles

**GET** `/api/intervals`

Retourne la liste de tous les intervalles de temps disponibles.

**Exemple de réponse :**
```json
{
  "intervals": ["1d", "1h"]
}
```

---

### 4. Données historiques

**GET** `/api/historical/{symbol}`

Récupère les données historiques pour un symbole donné.

**Paramètres de chemin :**
- `symbol` (required) : Symbole de la cryptomonnaie (ex: BTCUSDT)

**Paramètres de requête :**
- `interval` (optional) : Intervalle de temps (défaut: "1d")
- `start_time` (optional) : Date/heure de début au format ISO (ex: "2024-01-01T00:00:00Z")
- `end_time` (optional) : Date/heure de fin au format ISO
- `limit` (optional) : Nombre maximum d'enregistrements (défaut: 1000, max: 10000)

**Exemples d'utilisation :**

```bash
# Récupérer les 1000 derniers enregistrements journaliers de BTC
curl "http://localhost:8000/api/historical/BTCUSDT?interval=1d"

# Récupérer les données entre deux dates
curl "http://localhost:8000/api/historical/BTCUSDT?start_time=2024-01-01T00:00:00Z&end_time=2024-12-31T23:59:59Z"

# Limiter à 100 enregistrements
curl "http://localhost:8000/api/historical/BTCUSDT?limit=100"
```

**Exemple de réponse :**
```json
[
  {
    "symbol": "BTCUSDT",
    "interval": "1d",
    "open_time": "2024-01-01T00:00:00+00:00",
    "open": 42500.5,
    "high": 43200.0,
    "low": 42000.0,
    "close": 42800.25,
    "volume": 15234.567,
    "close_time": "2024-01-01T23:59:59+00:00"
  },
  "..."
]
```

---

### 5. Dernières données

**GET** `/api/latest/{symbol}`

Récupère les N enregistrements les plus récents pour un symbole.

**Paramètres de chemin :**
- `symbol` (required) : Symbole de la cryptomonnaie

**Paramètres de requête :**
- `interval` (optional) : Intervalle de temps (défaut: "1d")
- `count` (optional) : Nombre d'enregistrements récents (défaut: 30, max: 365)

**Exemples d'utilisation :**

```bash
# Récupérer les 30 derniers jours de BTC
curl "http://localhost:8000/api/latest/BTCUSDT"

# Récupérer les 90 derniers jours d'ETH
curl "http://localhost:8000/api/latest/ETHUSDT?count=90"
```

**Exemple de réponse :**
```json
[
  {
    "symbol": "BTCUSDT",
    "interval": "1d",
    "open_time": "2024-01-01T00:00:00+00:00",
    "open": 42500.5,
    "high": 43200.0,
    "low": 42000.0,
    "close": 42800.25,
    "volume": 15234.567,
    "close_time": "2024-01-01T23:59:59+00:00"
  },
  "..."
]
```

---

### 6. Statistiques agrégées

**GET** `/api/stats/{symbol}`

Calcule des statistiques agrégées pour un symbole sur une période donnée.

**Paramètres de chemin :**
- `symbol` (required) : Symbole de la cryptomonnaie

**Paramètres de requête :**
- `interval` (optional) : Intervalle de temps (défaut: "1d")
- `start_time` (optional) : Date/heure de début au format ISO
- `end_time` (optional) : Date/heure de fin au format ISO

**Exemples d'utilisation :**

```bash
# Statistiques globales pour BTC
curl "http://localhost:8000/api/stats/BTCUSDT"

# Statistiques pour une période spécifique
curl "http://localhost:8000/api/stats/BTCUSDT?start_time=2024-01-01T00:00:00Z&end_time=2024-12-31T23:59:59Z"
```

**Exemple de réponse :**
```json
{
  "symbol": "BTCUSDT",
  "interval": "1d",
  "count": 365,
  "avg_close": 45678.90,
  "min_low": 38000.0,
  "max_high": 52000.0,
  "total_volume": 5678900.123,
  "first_open_time": "2024-01-01T00:00:00+00:00",
  "last_open_time": "2024-12-31T00:00:00+00:00"
}
```

---

## Documentation interactive

Une fois l'API lancée, vous pouvez accéder à la documentation interactive Swagger UI sur :

```
http://localhost:8000/docs
```

Et à la documentation ReDoc sur :

```
http://localhost:8000/redoc
```

---

## Exemples d'utilisation avec JavaScript/TypeScript

### Fetch API (vanilla JavaScript)

```javascript
// Récupérer les symboles disponibles
async function getSymbols() {
  const response = await fetch('http://localhost:8000/api/symbols');
  const data = await response.json();
  console.log(data.symbols);
}

// Récupérer les données historiques
async function getHistoricalData(symbol, startDate, endDate) {
  const params = new URLSearchParams({
    interval: '1d',
    start_time: startDate,
    end_time: endDate
  });
  
  const response = await fetch(
    `http://localhost:8000/api/historical/${symbol}?${params}`
  );
  const data = await response.json();
  return data;
}

// Récupérer les 30 derniers jours
async function getLatestData(symbol) {
  const response = await fetch(
    `http://localhost:8000/api/latest/${symbol}?count=30`
  );
  const data = await response.json();
  return data;
}
```

### Axios (JavaScript/TypeScript)

```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Créer une instance axios
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Récupérer les données historiques
async function fetchHistoricalData(symbol, startDate, endDate) {
  try {
    const response = await api.get(`/api/historical/${symbol}`, {
      params: {
        interval: '1d',
        start_time: startDate,
        end_time: endDate,
        limit: 1000
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching data:', error);
    throw error;
  }
}

// Récupérer les statistiques
async function fetchStats(symbol) {
  try {
    const response = await api.get(`/api/stats/${symbol}`, {
      params: {
        interval: '1d'
      }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching stats:', error);
    throw error;
  }
}
```

---

## Exemples d'utilisation avec Python

```python
import requests
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000"

def get_symbols():
    """Récupérer la liste des symboles."""
    response = requests.get(f"{API_BASE_URL}/api/symbols")
    response.raise_for_status()
    return response.json()["symbols"]

def get_historical_data(symbol, days=30):
    """Récupérer les données historiques."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    params = {
        "interval": "1d",
        "start_time": start_date.isoformat(),
        "end_time": end_date.isoformat()
    }
    
    response = requests.get(
        f"{API_BASE_URL}/api/historical/{symbol}",
        params=params
    )
    response.raise_for_status()
    return response.json()

def get_latest_data(symbol, count=30):
    """Récupérer les dernières données."""
    params = {"count": count}
    response = requests.get(
        f"{API_BASE_URL}/api/latest/{symbol}",
        params=params
    )
    response.raise_for_status()
    return response.json()

def get_stats(symbol):
    """Récupérer les statistiques."""
    response = requests.get(f"{API_BASE_URL}/api/stats/{symbol}")
    response.raise_for_status()
    return response.json()

# Utilisation
if __name__ == "__main__":
    # Lister les symboles
    symbols = get_symbols()
    print(f"Symboles disponibles: {symbols}")
    
    # Récupérer les données BTC
    btc_data = get_historical_data("BTCUSDT", days=90)
    print(f"Récupéré {len(btc_data)} enregistrements pour BTC")
    
    # Statistiques
    stats = get_stats("BTCUSDT")
    print(f"Prix moyen: {stats['avg_close']}")
```

---

## Codes d'erreur

- `200` : Succès
- `400` : Requête invalide (paramètres incorrects)
- `404` : Données non trouvées pour les paramètres spécifiés
- `500` : Erreur serveur interne
- `503` : Service indisponible (problème de connexion à la base de données)

---

## CORS

L'API est configurée pour accepter les requêtes cross-origin depuis n'importe quelle origine (`allow_origins=["*"]`).

