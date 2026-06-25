# monitoring/grafana/provisioning — Provisioning Grafana

Ce dossier attend la configuration de provisioning automatique Grafana (Semaine 5, C11).

## Fichier à créer

### `datasources.yml`

Configure Prometheus comme datasource automatiquement au démarrage de Grafana :

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

Ce fichier est monté dans le conteneur Grafana via `docker-compose.yml` :
```yaml
volumes:
  - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
```

## Résultat

Au `docker-compose up`, Grafana démarre avec Prometheus déjà configuré
comme datasource — aucune configuration manuelle requise.
