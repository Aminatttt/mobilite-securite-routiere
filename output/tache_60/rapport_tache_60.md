# Tâche 60 — Analyse des erreurs et cas d'échec du modèle

Échantillon Test : 1,613 accidents, dont 78 réellement graves.
Seuil de décision utilisé : 0.111 (validé en tâche 57).

## Répartition des prédictions
- Vrais négatifs (léger correctement détecté) : 1356
- Faux positifs (fausse alerte) : 179
- Faux négatifs (**grave raté**) : 67
- Vrais positifs (grave détecté) : 11

## Constat principal
Sur 78 accidents réellement graves dans le Test, le modèle en détecte 11 et en rate 67 (86% des cas graves passent inaperçus).

## Limite structurelle (pas un bug)
Avec seulement 78 accidents graves dans tout le jeu de test, chaque cas individuel pèse lourd dans les métriques (1 cas = ~1,3 point de recall). Le modèle ne dispose pas d'assez de cas positifs, ni de variables suffisamment discriminantes (cf. tâche 49 : corrélations faibles), pour identifier un pattern fiable de gravité. Ce n'est pas un problème d'implémentation mais une vraie limite du signal disponible dans les données.

## Recommandation
Pour progresser sur ce point, il faudrait des variables actuellement absentes du dataset enrichi : vitesse au moment du choc, type de route/infrastructure, port de la ceinture/casque, type de véhicule impliqué. Ces variables sont présentes dans les données BAAC brutes mais ont été exclues du modèle pour éviter la fuite de données (tâche 52) — elles caractérisent l'accident lui-même plutôt que son contexte, donc leur intégration demanderait de vérifier au cas par cas qu'elles sont bien connues *avant* l'accident, pas déduites après coup.