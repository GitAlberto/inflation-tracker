# Spécifications Fonctionnelles — Inflation Tracker (C14)

**Projet :** Inflation Tracker France — B3 RNCP Développeur IA  
**Auteur :** Alberto Bongue  
**Version :** 1.0 — 2026-07  
**Issue GitHub :** #18 (C14)

---

## 1. Contexte et objectif

### Problème

L'inflation est un phénomène économique quotidien, mais les données publiques qui
la mesurent (INSEE, BCE, Eurostat) sont dispersées, au format technique (SDMX, CSV
multi-colonnes, API REST avec codes COICOP), et inaccessibles pour un utilisateur
non statisticien.

> Le kebab coûtait **3,50 €** en 2019. Il en coûte **7 €** en 2026.
> L'utilisateur ressent l'inflation, mais ne peut pas la quantifier ni anticiper
> son évolution par catégorie de produit.

### Objectif

Fournir une application web permettant à un utilisateur non expert de :

1. **Visualiser** l'évolution historique de l'IPC France depuis 1996
2. **Comparer** les sources et les catégories de produits
3. **Anticiper** l'évolution de l'inflation par catégorie (modèle Prophet)
4. **Évaluer** la fiabilité du modèle de prédiction

---

## 2. Utilisateurs cibles

| Persona | Profil | Besoin principal |
|---|---|---|
| **Analyste économique** | Maîtrise des concepts IPC, utilise Excel/Python | Accès rapide aux données multi-sources pour comparaison |
| **Étudiant en économie** | Connaît les bases de l'inflation | Comprendre la structure des données et valider des hypothèses |
| **Citoyen curieux** | Aucune formation statistique | Comprendre pourquoi ses courses coûtent plus cher |
| **Jury RNCP** | Évalue les compétences techniques | Voir la cohérence entre pipeline ML et interface |

---

## 3. User stories

### Module 1 — Analyse Historique

---

**US-01 — Visualisation de l'évolution IPC**

> En tant qu'**analyste**, je veux visualiser l'évolution de l'IPC pour une source,
> un pays et une ou plusieurs catégories sur une période choisie,
> afin de comparer les tendances historiques.

Critères d'acceptation :
- [ ] L'utilisateur peut sélectionner une source parmi : INSEE, ECB, EUROSTAT, DATAGOUV
- [ ] L'utilisateur peut sélectionner un pays (liste dépend de la source)
- [ ] L'utilisateur peut sélectionner 1 à 5 catégories IPC simultanément
- [ ] L'utilisateur peut définir la période via un slider 1996–2025
- [ ] Le graphique affiche une courbe par catégorie avec couleurs distinctes
- [ ] Un tableau de statistiques descriptives (min, max, moyenne, variation) s'affiche sous le graphique
- [ ] Si aucune donnée n'est disponible pour la combinaison choisie, un message explicite s'affiche

---

**US-02 — Comparaison multi-catégories**

> En tant qu'**étudiant**, je veux superposer l'évolution de l'alimentation et
> de l'énergie sur le même graphique, afin d'identifier laquelle a le plus contribué
> à l'inflation post-COVID.

Critères d'acceptation :
- [ ] La sélection multiple (max 5) est permise via un widget multiselect
- [ ] Chaque courbe a une couleur distincte et une entrée dans la légende
- [ ] Le tooltip au survol affiche toutes les valeurs pour la date pointée
- [ ] Les statistiques du tableau sont calculées individuellement par catégorie

---

### Module 2 — Analyse par Catégorie

---

**US-03 — Deep-dive sur une catégorie**

> En tant qu'**analyste**, je veux voir l'évolution détaillée d'une seule catégorie
> avec sa variation annuelle (YoY) et sa saisonnalité mensuelle,
> afin d'identifier des cycles ou des ruptures structurelles.

Critères d'acceptation :
- [ ] L'utilisateur sélectionne une catégorie et une source
- [ ] Le graphique principal montre l'IPC absolu + la variation YoY sur un second axe
- [ ] Une heatmap mensuelle (années × mois) affiche l'intensité de la variation
- [ ] Les statistiques clés (min, max, pic, mois le plus inflationniste) sont affichées
- [ ] L'utilisateur peut filtrer par plage d'années via un slider

---

**US-04 — Changement de source**

> En tant qu'**analyste**, je veux basculer entre DATAGOUV (depuis 1996) et INSEE
> (depuis 2020) pour la même catégorie, afin de disposer de la profondeur historique
> maximale tout en identifiant les divergences entre sources.

Critères d'acceptation :
- [ ] Un sélecteur de source est disponible, avec DATAGOUV sélectionné par défaut
- [ ] Le changement de source recharge les données sans recharger la page
- [ ] Si la source sélectionnée ne contient pas la catégorie choisie, un message l'indique
- [ ] La note « base 2025 » est visible quand DATAGOUV est sélectionné

---

### Module 3 — Prédictions Prophet

---

**US-05 — Prédiction Prophet par catégorie**

> En tant qu'**étudiant**, je veux obtenir une prédiction de l'IPC Alimentation
> pour les 12 prochains mois avec un intervalle de confiance,
> afin d'estimer la hausse attendue de mon budget courses.

Critères d'acceptation :
- [ ] L'utilisateur sélectionne une catégorie parmi les 13 disponibles
- [ ] L'utilisateur ajuste l'horizon de prédiction via un slider (1–36 mois)
- [ ] Le graphique superpose l'historique réel (INSEE) et la prédiction Prophet
- [ ] L'intervalle de confiance 80% est représenté en zone semi-transparente
- [ ] Une ligne verticale pointillée sépare visuellement historique et prédiction
- [ ] Les métriques MAE/RMSE/MAPE de la catégorie sont affichées dans la sidebar
- [ ] La variation totale prédite (premier → dernier mois) est affichée en métrique
- [ ] Un tableau détaillé des valeurs prédites est disponible dans un expander

---

**US-06 — Évaluation de la fiabilité**

> En tant qu'**analyste**, je veux savoir si la prédiction pour l'énergie est
> plus ou moins fiable que pour l'alimentation,
> afin de pondérer mes décisions en fonction de l'incertitude du modèle.

Critères d'acceptation :
- [ ] Les métriques MAE et MAPE sont affichées par catégorie sélectionnée
- [ ] MAE < 1 pt IPC = modèle fiable, > 5 = à interpréter avec précaution
- [ ] Le contexte d'évaluation (train 2020-2024, eval 2025) est clairement indiqué

---

### Module 4 — Métriques Modèle

---

**US-07 — Vue d'ensemble des performances Prophet**

> En tant que **jury RNCP**, je veux voir la performance du modèle sur l'ensemble
> des 13 catégories IPC,
> afin d'évaluer la pertinence de l'approche Prophet pour ce cas d'usage.

Critères d'acceptation :
- [ ] Un bar chart horizontal montre la MAE de chaque catégorie
- [ ] Les barres sont colorées : vert ≤ 1 pt, orange ≤ 5 pts, rouge > 5 pts
- [ ] Un scatter RMSE vs MAE permet d'identifier les outliers
- [ ] Un tableau complet MAE/RMSE/MAPE avec formatage numérique est disponible
- [ ] La méthodologie d'évaluation (split temporel strict, pas de shuffle) est documentée

---

### Infrastructure transversale

---

**US-08 — Statut des services**

> En tant qu'**utilisateur**, je veux savoir si les APIs sont opérationnelles
> avant d'utiliser l'application,
> afin de distinguer une erreur de mes saisies d'une panne de service.

Critères d'acceptation :
- [ ] La page d'accueil affiche le statut (✅/❌) des deux APIs (data 8001, modèle 8002)
- [ ] Si une API est hors ligne, les pages qui en dépendent affichent un message explicite
- [ ] Le message indique la commande pour relancer le service manquant

---

**US-09 — Performance acceptable**

> En tant qu'**utilisateur**, je veux que les graphiques se chargent en moins de 5 secondes,
> afin que l'expérience ne soit pas frustrante lors de la démonstration.

Critères d'acceptation :
- [ ] Les données historiques (API data) se chargent en < 3s (cache Streamlit 5 min)
- [ ] Les prédictions Prophet se chargent en < 15s (modèle .pkl + Prophet, cache 1 min)
- [ ] Un spinner est affiché pendant le chargement des prédictions
- [ ] Les appels API ont un timeout configuré pour éviter les blocages infinis

---

## 4. Parcours utilisateur principal (Use Case)

```
Utilisateur ouvre l'application
│
├─► Page Accueil
│     ├─ KPIs IPC 2022-2025 visibles immédiatement
│     ├─ Statut APIs affiché dans la sidebar
│     └─ Navigation vers les 4 pages
│
├─► [Question : "Qu'est-ce qui a augmenté le plus ?"]
│     └─► Analyse Historique
│           ├─ Source : DATAGOUV (profondeur depuis 1996)
│           ├─ Catégories : Alimentation + Énergie
│           └─ Graphique superposé → réponse visuelle
│
├─► [Question : "L'alimentation est-elle saisonnière ?"]
│     └─► Analyse par Catégorie
│           ├─ Catégorie : Alimentation
│           ├─ Heatmap mensuelle → pic visible en janvier
│           └─ Variation YoY → tendance structurelle identifiée
│
└─► [Question : "Combien vont coûter mes courses dans 6 mois ?"]
      └─► Prédictions
            ├─ Catégorie : Alimentation
            ├─ Horizon : 6 mois
            ├─ Prophet prédit +X pts IPC avec IC 80%
            └─ MAE = 0.4 pts → fiabilité confirmée
```

---

## 5. Exigences non-fonctionnelles

| Exigence | Valeur cible | Justification |
|---|---|---|
| Temps de chargement données | < 3s | Cache Streamlit 5 min, API locale |
| Temps de prédiction Prophet | < 15s | Chargement .pkl + calcul Prophet |
| Disponibilité en démo | 100% | Stack locale Docker, pas de dépendance réseau |
| Couverture tests API | > 70% | Mesurée par pytest-cov en CI |
| Volume données supporté | 3,68M lignes | PostgreSQL + index sur (source, pays, categorie) |
| Navigateurs supportés | Chrome, Firefox, Edge | Rendu Plotly + Streamlit standard |

---

## 6. Hors périmètre (Out of Scope)

- Authentification utilisateur — application de démonstration, pas de données personnelles
- Notifications temps réel — l'application est une consultation, pas une alerte
- Prédictions à plus de 36 mois — horizon Prophet non fiable au-delà
- Données infra-mensuelles (hebdomadaires, quotidiennes) — les sources INSEE/ECB sont mensuelles
- Comparaison internationale des prix absolus (≠ indices) — hors champ du projet

---

## 7. Limites assumées

- **DATAGOUV base 2025** : depuis le rebasage INSEE, les valeurs DATAGOUV (base 2025=100)
  ne sont pas directement comparables aux valeurs INSEE API (base 2015=100). L'évolution
  relative reste valide ; la comparaison de valeurs absolues entre sources est à éviter.

- **Prédictions Prophet** : le modèle est entraîné sur 2020-2024 (5 ans, 60 points).
  La précision se dégrade au-delà de 12 mois et sur les catégories très volatiles (Énergie).

- **Données OpenFoodFacts** : la source prix alimentaires est collectée mais non intégrée
  dans les prédictions — volume insuffisant et couverture géographique partielle.
