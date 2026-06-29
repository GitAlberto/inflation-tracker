=====================================
Erreur PySpark : echec d'inatallation cause par manque de java
Resolution : installer java et redemarer le terminal
"""""""""""""""""
Java 21 tourne. Le souci c'était simple : le MSI a installé Java mais n'a pas mis à jour le PATH de la session en cours — Windows ne recharge pas les variables d'environnement dans un terminal déjà ouvert. Fermer et rouvrir VS Code a suffi à tout charger.
=====================================
création des tables : 
création des 5 tables des 5 différents sources de données avec les identifiants uuid et la table finale d'agrégation.
=====================================