# monitoring/grafana — Configuration Grafana

Ce dossier attend la configuration Grafana pour le provisioning automatique (Semaine 5, C11/C20).

## Structure

```
grafana/
├── dashboards/     → fichiers JSON des dashboards importés automatiquement
└── provisioning/   → datasources et dashboard providers (chargés au démarrage)
```

## Fonctionnement

Grafana charge automatiquement au démarrage :
1. Les datasources depuis `provisioning/datasources.yml`
2. Les dashboards depuis `dashboards/*.json`

Cela permet un `docker-compose up` reproductible sans configuration manuelle.

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `provisioning/datasources.yml` | Configure Prometheus comme source de données |
| `dashboards/model_dashboard.json` | Dashboard métriques modèle Prophet (C11) |
| `dashboards/app_dashboard.json` | Dashboard métriques application Streamlit (C20) |
