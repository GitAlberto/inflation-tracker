# monitoring/grafana/dashboards — Dashboards Grafana

Ce dossier attend les fichiers JSON des dashboards Grafana (Semaine 5, C11/C20).

## Fichiers à créer

### `model_dashboard.json` (C11)

Dashboard de monitoring du modèle Prophet :

| Panel | Métrique Prometheus | Seuil d'alerte |
|---|---|---|
| MAE temps réel | `prediction_mae` | > 2 points IPC |
| Latence prédictions | `prediction_latency_seconds` | > 2s |
| Nombre de prédictions | `predictions_total` | — |
| Taux d'erreurs API | `api_errors_total` | > 5% |

### `app_dashboard.json` (C20)

Dashboard de monitoring de l'application Streamlit :

| Panel | Métrique Prometheus |
|---|---|
| Requêtes utilisateur par catégorie | `app_requests_total` |
| Erreurs appel API modèle | `app_api_errors_total` |
| Latence Streamlit end-to-end | `app_latency_seconds` |

## Comment générer ces fichiers

1. Créer le dashboard dans l'interface Grafana
2. Dashboard settings → JSON Model → copier
3. Sauvegarder ici en `.json`

Les fichiers sont chargés automatiquement via `provisioning/`.
