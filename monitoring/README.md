# monitoring — Stack Prometheus + Grafana (C11, C20)

Ce dossier attend la configuration complète du monitoring (Semaine 5, C11 + C20).

## Structure

```
monitoring/
├── prometheus.yml      → configuration Prometheus (targets à scraper)
├── alerts.yml          → règles d'alertes Prometheus
└── grafana/
    ├── dashboards/     → fichiers JSON des dashboards Grafana
    └── provisioning/   → configuration automatique Grafana
```

## Stack

```
API FastAPI (/metrics) → Prometheus (scrape toutes les 15s) → Grafana (dashboards)
                                                            → Alertes (alerts.yml)
```

## Ports

| Service | Port |
|---|---|
| Prometheus | 9090 |
| Grafana | 3000 |
| API modèle | 8000 |
| API data | 8001 |
| Streamlit | 8501 |

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `prometheus.yml` | Définit les targets à scraper (3 services) |
| `alerts.yml` | 3 règles : MAE trop élevée, latence élevée, taux d'erreurs |

## Preuve requise (C11, C20)

- Dashboard Grafana modèle avec métriques en temps réel
- Dashboard Grafana application
- Screenshot d'une alerte déclenchée
