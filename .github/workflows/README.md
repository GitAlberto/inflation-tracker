# .github/workflows — Pipelines CI/CD

Ce dossier attend les 3 pipelines GitHub Actions du projet (Semaine 6-7).

## Fichiers à créer

| Fichier | Compétence | Contenu |
|---|---|---|
| `ci_data.yml` | C13 | Tests collecte + agrégation + API data — Bloc 1 |
| `ci_model.yml` | C13 | Tests modèle + API modèle — Bloc 2 |
| `ci_app.yml` | C18/C19 | Tests application Streamlit — Bloc 3 |

## Comportement attendu

- Déclenchement sur chaque `push` et `pull_request`
- Python 3.12
- `pip install -r requirements.txt`
- `pytest` avec couverture > 80%
- Badge vert visible sur le README

## Preuve requise (C13, C18)

Screenshot des 3 pipelines verts sur GitHub Actions.
