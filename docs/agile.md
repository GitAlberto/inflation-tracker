# Gestion de projet Agile — Inflation Tracker (C16)

**Projet :** Inflation Tracker France — B3 RNCP Développeur IA  
**Auteur :** Alberto Bongue  
**Méthode :** Kanban  
**Outil :** GitHub Projects  
**Board :** https://github.com/users/GitAlberto/projects/2

---

## 1. Méthode choisie : Kanban

Le projet adopte une méthode **Kanban** plutôt que Scrum, pour trois raisons :

1. **Projet solo** — pas de cérémonies d'équipe (daily, planning poker) à organiser
2. **Périmètre évolutif** — les compétences RNCP ont émergé progressivement ; le backlog s'est construit en avançant
3. **Flux continu** — chaque compétence (C1–C21) représente une unité de travail indépendante, sans dépendance temporelle stricte entre toutes

---

## 2. Structure du board GitHub Projects

Le board est organisé en **4 colonnes** reflétant l'état réel de chaque tâche :

| Colonne | Signification |
|---|---|
| **Backlog** | Compétences identifiées, non démarrées |
| **In Progress** | En cours de développement |
| **Review** | Terminé, en attente de validation (tests CI, relecture) |
| **Done** | Livré, commité, issue fermée |

Chaque carte du board correspond à **une issue GitHub**, elle-même liée à une ou plusieurs compétences RNCP via des labels `C1` à `C21`.

---

## 3. Workflow : issue → commit → compétence

```
1. Création d'une issue GitHub
   └─ Titre : "[C8] Modèle Prophet IPC France"
   └─ Label : compétence concernée (ex: C8)
   └─ Description : contexte, critères de done

2. Déplacement de la carte → "In Progress" sur le board

3. Développement local + commits référençant l'issue
   └─ Convention : feat(C8): ... #14
   └─ Le numéro d'issue (#14) lie automatiquement le commit à la carte

4. Push sur la branche AlbertoFinB3
   └─ Déclenchement des CI (tests, lint)
   └─ Vérification des checks GitHub Actions

5. Déplacement → "Done" + fermeture de l'issue
   └─ La carte affiche le commit et les checks associés
```

---

## 4. Issues et compétences couvertes

| Issue | Label | Compétence | Statut |
|---|---|---|---|
| #1 | C1 | Expression des besoins | ✅ Done |
| #2 | C2 | Architecture technique | ✅ Done |
| #3 | C3 | Pipeline ETL multi-sources | ✅ Done |
| #4 | C4 | Base de données PostgreSQL | ✅ Done |
| #5 | C5 | API Data REST (FastAPI) | ✅ Done |
| #6 | C6 | Documentation API (OpenAPI) | ✅ Done |
| #7 | C7 | Benchmark Prophet vs ARIMA vs Holt-Winters | ✅ Done |
| #8 | C8 | Modèle Prophet 12 catégories INSEE | ✅ Done |
| #9 | C9 | API Modèle REST (prédictions) | ✅ Done |
| #10 | C10 | Application Streamlit 4 pages | ✅ Done |
| #11 | C11 | Collecte Eurostat (PySpark) | ✅ Done |
| #12 | C12 | Tests unitaires pipeline + modèle | ✅ Done |
| #13 | C13 | Tests API + couverture > 70% | ✅ Done |
| #14 | C14 | Spécifications fonctionnelles | ✅ Done |
| #15 | C15 | Interface utilisateur thème financier | ✅ Done |
| #16 | C16 | Gestion de projet Agile (ce document) | ✅ Done |
| #17 | C17 | Accessibilité et ergonomie UI | ✅ Done |
| #18 | C18 | CI/CD GitHub Actions | ✅ Done |
| #19 | C19 | Conteneurisation Docker | ✅ Done |
| #20 | C20 | Monitoring Prometheus + Grafana | ✅ Done |
| #21 | C21 | Incident postmortem ETL | ✅ Done |

---

## 5. Conventions de commit

Chaque commit suit la convention **Conventional Commits** avec référence à l'issue :

```
<type>(<compétences>): <description courte> #<numéro-issue>

feat(C8): entraînement Prophet 12 catégories INSEE #8
fix(C12/C13): tests 13→12 catégories COICOP #12
docs(C14): spécifications fonctionnelles 9 user stories #14
```

Types utilisés :
- `feat` — nouvelle fonctionnalité ou livrable
- `fix` — correction de bug ou d'anomalie
- `docs` — documentation uniquement
- `ci` — modification des workflows CI/CD
- `refactor` — restructuration sans changement de comportement

---

## 6. Gestion des incidents

Les anomalies détectées en cours de projet sont tracées via des issues dédiées
et documentées sous forme de **postmortem** dans `docs/`.

Exemple : incident pipeline ETL du 2026-07-18 → issue #21 → `docs/incident_2026-07-18.md`

Ce processus garantit la **traçabilité complète** : du symptôme observé à la
correction commitée, en passant par l'analyse des causes racines.

---

## 7. Branches

| Branche | Rôle |
|---|---|
| `main` | Branche stable — merge via Pull Request uniquement |
| `AlbertoFinB3` | Branche de développement principale |

Toutes les livraisons passent par une **Pull Request** de `AlbertoFinB3` vers `main`,
déclenchant les checks CI automatiques avant tout merge.
