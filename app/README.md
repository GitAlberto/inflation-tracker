# app — Application Streamlit (C17)

Ce dossier attend l'application Streamlit de visualisation et prédiction (Semaine 7, C17).

## Fichiers à créer

| Fichier | Rôle |
|---|---|
| `main.py` | Interface Streamlit principale |
| `api_client.py` | Client HTTP vers l'API modèle (C10) |
| `currency.py` | Conversion devises (optionnel) |

## Fonctionnalités attendues (User Stories C14)

| US | Description | Critère |
|---|---|---|
| US1 | Évolution historique IPC par catégorie | Graphique interactif avec slider de dates |
| US2 | Prédiction d'inflation sur 6 mois | Courbe avec intervalle de confiance |
| US3 | Décomposition des composantes | Tendance + saisonnalité Prophet |
| US4 | Gestion erreur API indisponible | Message clair sans crash |

## Stack technique

- `streamlit` — interface
- `plotly` — graphiques interactifs
- `requests` — appels API modèle

## Preuve requise (C17)

- Capture de l'application fonctionnelle
- Démonstration du cas d'erreur API (US4)
- Tests dans `tests/test_app.py`

## Lancement

```bash
streamlit run app/main.py
```
