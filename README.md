SEP25_CDE_OPA_GROUPE_1
==============================

## Définition du projet

De nos jours, le monde des crypto commence à prendre une place importante et grossit. Il s’agit tout simplement de
marchés financiers assez volatiles et instables se basant sur la technologie de la Blockchain.

Le but de ce projet est de créer un bot de trading, basé sur un modèle de Machine Learning, qui investira sur des
marchés crypto.

## Etapes

- Récupération des données via l'API Binance
    - ✅ Données historiques, pour l'entraînement des modèles
    - ✅ Stockage dans MongoDB
    - ✅ API REST pour interroger les données
    - Données en temps réel, pour le déploiement du bot de trading
- Exploration et analyse des données
- Préparation des données
- Entraînement de modèles de Machine Learning
- Évaluation des modèles
- Déploiement du bot de trading

## Architecture technique

### Base de données

- **PostgreSQL** : Métadonnées et configuration
- **MongoDB** : Données historiques de cryptomonnaies

### Déploiement

#### Option 1 : Docker (Recommandé)

Démarrer toute la stack en une commande :

```bash
# Linux / Mac / WSL
./start_stack.sh

# Windows
start_stack.bat
```

Cette commande démarre :

- 🐳 MongoDB (port 27025)
- 🐘 PostgreSQL (port 5435)  
- 🔧 PgAdmin (port 5436)
- 🚀 API FastAPI (port 8000)

#### Option 2 : Installation locale

1. Installer les dépendances :

```bash
pip install -r requirements.txt
```

2. Configurer le fichier `.env` (voir `.env.example`)

3. Initialiser PostgreSQL :

```bash
python init_database.py
```

4. Lancer l'API :

```bash
python run_api.py
```

L'API sera accessible sur `http://localhost:8000`

### API REST

Une API FastAPI permet d'interroger les données historiques stockées dans MongoDB.

#### Documentation de l'API

- Documentation interactive : `http://localhost:8000/docs`
- Documentation complète : [references/API_DOCUMENTATION.md](references/API_DOCUMENTATION.md)

#### Endpoints principaux

- `GET /health` - Health check
- `GET /api/symbols` - Liste des symboles disponibles
- `GET /api/intervals` - Liste des intervalles disponibles
- `GET /api/historical/{symbol}` - Données historiques
- `GET /api/latest/{symbol}` - Dernières données
- `GET /api/stats/{symbol}` - Statistiques agrégées

## Listes des symboles utilisés

- BTCUSDT
- ETHUSDT
- SOLUSDT

## Documentation et liens utiles

- [Documentation Binance API](https://developers.binance.com/docs/binance-spot-api-docs)
- [Documentation FastAPI](https://fastapi.tiangolo.com/)
- [Documentation MongoDB](https://docs.mongodb.com/)
- [Documentation PostgreSQL](https://www.postgresql.org/docs/)
- [Documentation Docker](https://docs.docker.com/)

Project Organization
------------

    ├── LICENSE
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
    │
    ├── logs               <- Logs from training and predicting
    │
    ├── models             <- Trained and serialized models, model predictions, or model summaries
    │
    ├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
    │                         the creator's initials, and a short `-` delimited description, e.g.
    │                         `1.0-jqp-initial-data-exploration`.
    │
    ├── references         <- Data dictionaries, manuals, and all other explanatory materials.
    │   └── API_DOCUMENTATION.md
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    │
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
    │                         generated with `pip freeze > requirements.txt`
    │
    ├── src                <- Source code for use in this project.
    │   ├── __init__.py    <- Makes src a Python module
    │   │
    │   ├── api            <- FastAPI REST API for querying data
    │   │   ├── __init__.py
    │   │   ├── app.py     <- Main FastAPI application
    │   │   ├── models.py  <- Pydantic models for request/response
    │   │   └── queries.py <- MongoDB query functions
    │   │
    │   ├── data           <- Scripts to download or generate data
    │   │   ├── make_dataset.py
    │   │   ├── config.py  <- Configuration settings
    │   │   ├── connector/ <- Database connectors
    │   │   ├── fetch_historical_daily.py <- Fetch and store historical data
    │   │   └── historical_data.py <- Historical data retrieval
    │   │
    │   ├── features       <- Scripts to turn raw data into features for modeling
    │   │   └── build_features.py
    │   │
    │   ├── models         <- Scripts to train models and then use trained models to make
    │   │   │                 predictions
    │   │   ├── predict_model.py
    │   │   └── train_model.py
    │   │
    │   ├── visualization  <- Scripts to create exploratory and results oriented visualizations
    │   │   └── visualize.py
    │   └── config         <- Describe the parameters used in train_model.py and predict_model.py
    └── run_api.py         <- Script to run the FastAPI server
    └── start_stack.sh     <- Script to start the entire Docker stack (MongoDB, PostgreSQL, API)
    └── start_stack.bat    <- Script Windows to start the entire Docker stack

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
