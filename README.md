SEP25_CDE_OPA_GROUPE_1
==============================

## Définition du projet

De nos jours, le monde des crypto commence à prendre une place importante et grossit. Il s’agit tout simplement de
marchés financiers assez volatiles et instables se basant sur la technologie de la Blockchain.

Le but de ce projet est de créer un bot de trading, basé sur un modèle de Machine Learning, qui investira sur des
marchés crypto.

## Etapes

- Récupération des données via l'API Binance
    - Données historiques, pour l'entraînement des modèles
    - Données en temps réel, pour le déploiement du bot de trading
- Exploration et analyse des données
- Préparation des données
- Entraînement de modèles de Machine Learning
- Évaluation des modèles
- Déploiement du bot de trading

## Listes des symboles utilisés

- BTCUSDT
- ETHUSDT
- SOLUSDT

## Documentation et liens utiles

- [Documentation Binance API](https://developers.binance.com/docs/binance-spot-api-docs)
- [Tutoriel sur l'utilisation de l'API Binance avec Python](https://python-binance.readthedocs.io/en/latest/)
- [Liste et cours des cryptomonnaies](https://fr.tradingview.com/markets/cryptocurrencies/prices-all/)

Project Organization
------------

    ├── LICENSE
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original, immutable data dump.
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
    │
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    │
    ├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
    │                         generated with `pip freeze > requirements.txt`
    │
    ├── src                <- Source code for use in this project.
    │   ├── __init__.py    <- Makes src a Python module
    │   │
    │   ├── data           <- Scripts to download or generate data
    │   │   └── make_dataset.py
    │   │
    │   ├── features       <- Scripts to turn raw data into features for modeling
    │   │   └── build_features.py
    │   │
    │   ├── models         <- Scripts to train models and then use trained models to make
    │   │   │                 predictions
    │   │   ├── predict_model.py
    │   │   └── train_model.py
    │   │
    │   ├── visualization  <- Scripts to create exploratory and results oriented visualizations
    │   │   └── visualize.py
    │   └── config         <- Describe the parameters used in train_model.py and predict_model.py

--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
