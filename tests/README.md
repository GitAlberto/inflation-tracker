# tests — Suite de tests (C12, C18)

Ce dossier attend les tests automatisés du projet (Semaine 6-7, C12/C18).

## Fichiers à créer

| Fichier | Ce qui est testé | Compétence |
|---|---|---|
| `test_collect.py` | Chaque collecteur retourne un DataFrame non vide | C12 |
| `test_aggregate.py` | Dataset final : colonnes attendues, pas de nulls sur colonnes clés | C12 |
| `test_api_data.py` | Endpoints API data : 200, 401, 422 | C12 |
| `test_model.py` | MAE < seuil, format prédiction correct | C12 |
| `test_api_model.py` | `/predict` retourne les bons champs | C12 |
| `test_app.py` | Client API + gestion d'erreur | C18 |

## Objectif

- Couverture de code > 80% (`pytest-cov`)
- Tous les tests passent en local ET en CI (GitHub Actions)

## Lancement

```bash
pytest tests/ --cov=src --cov=api --cov=model --cov=app --cov-report=html
```

## Preuve requise (C12)

- Screenshot `pytest` avec résultats (nb tests, couverture)
- Badge couverture dans le README
