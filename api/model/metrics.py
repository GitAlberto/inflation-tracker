"""
=============================================================================
C11 — Métriques Prometheus — API modèle Prophet — inflation-tracker
=============================================================================
Définit les objets Prometheus exposés sur /metrics pour le scraping
par Prometheus et la visualisation Grafana.

Importé par :
    api/model/main.py   (middleware latence + startup MAE)
    api/model/routes/predict.py  (compteur prédictions par catégorie)

Issue GitHub : #17 (C11)
=============================================================================
"""

from prometheus_client import Counter, Gauge, Histogram

# Nombre de prédictions générées — labelisé par catégorie
# Permet de voir quelles catégories sont les plus demandées sur Grafana
predictions_total = Counter(
    "inflation_predictions_total",
    "Nombre total de prédictions Prophet générées",
    ["categorie"],
)

# Latence des requêtes /predict — histogramme pour calcul de percentiles (p50, p95, p99)
# Buckets : 0.1s → 30s pour couvrir le chargement de .pkl sur disque
prediction_latency_seconds = Histogram(
    "inflation_prediction_latency_seconds",
    "Temps de traitement des requêtes /predict en secondes",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# MAE par catégorie — jauge initialisée depuis metrics.json au démarrage de l'API
# Permet l'alerte automatique si la MAE dépasse un seuil (cf. alerts.yml)
prediction_mae = Gauge(
    "inflation_prediction_mae",
    "MAE du modèle Prophet par catégorie (évaluation 2025)",
    ["categorie"],
)

# Compteur d'erreurs API par type — pour le taux d'erreurs sur Grafana
# Types : "not_found" (404), "validation" (422), "server_error" (500)
api_errors_total = Counter(
    "inflation_api_errors_total",
    "Nombre d'erreurs API modèle par type d'erreur",
    ["error_type"],
)

# Nombre total de requêtes reçues — labelisé par méthode, route et statut HTTP
# Permet le calcul du taux de succès (requests sans erreur / total)
api_requests_total = Counter(
    "inflation_api_requests_total",
    "Nombre total de requêtes HTTP reçues par l'API modèle",
    ["method", "endpoint", "status_code"],
)
