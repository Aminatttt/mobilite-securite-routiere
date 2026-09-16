# Model Card — Prédiction de la gravité des accidents à Paris

*Tâche 61 — Phase 5 (Intelligence Artificielle) — Projet Mobilité & Sécurité Routière à Paris*

---

## 1. Objectif

Prédire si un accident de la route à Paris sera **grave** (au moins un tué ou un blessé
hospitalisé) ou **léger** (indemne ou blessé léger), à partir d'informations connues
**avant ou indépendamment** du déroulement de l'accident (météo, contexte temporel,
niveau de trafic, population du secteur).

**Usage visé** : exploration académique / démonstrateur d'analyse de risque. Ce n'est
**pas** un outil de décision opérationnelle (voir section 6 — Limites).

---

## 2. Données

| | |
|---|---|
| Source | `data/mobilite_paris.db`, table `FAIT_ACCIDENT_ENRICHI` |
| Périmètre | Paris intra-muros, année **2024 uniquement** |
| Volume | 9 132 usagers impliqués dans 4 191 accidents |
| Cible | `grave` = 1 si `grav` ∈ {2 (tué), 3 (blessé hospitalisé)}, sinon 0 |
| Distribution de la cible | 95,3 % non grave / **4,7 % grave** (déséquilibre fort, ratio 1:20) |
| Découpage Train/Test | **Temporel** (recommandé tâche 54) : Train = jours < 19/10/2024 (7 519 lignes), Test = jours ≥ 19/10/2024 (1 613 lignes) |

Le découpage temporel a été préféré à un découpage aléatoire pour éviter d'entraîner
le modèle sur des accidents qui, dans la réalité, se seraient produits après ceux du
jeu de test.

---

## 3. Variables utilisées (27 features)

Uniquement des variables **connues indépendamment du déroulement de l'accident** :
- **Contexte temporel** : année, mois, jour, jour de la semaine, semaine, trimestre, saison, week-end, jour férié
- **Météo** : précipitations, températures min/max/moyenne, indicateur de pluie
- **Trafic** : débit moyen (`q_moyen`), taux d'occupation (`k_moyen`), ratio de saturation, indicateur trafic élevé
- **Contexte géographique** : population du secteur

**Volontairement exclues (fuite de données, tâche 52)** : gravité elle-même, catégorie
d'usager, équipements de sécurité, type de collision, identifiants d'accident — toutes
des informations qui ne sont connues qu'*après* l'accident, ou qui définissent
directement la cible.

---

## 4. Modèles évalués

| Modèle | Variables | Seuil | ROC-AUC | PR-AUC | F1 (grave) |
|---|---|---|---|---|---|
| Régression logistique simple (tâche 55) | 4 (météo/saison/luminosité) | 0,5 | **0,5345** | — | 0,094 |
| Régression logistique (tâche 58) | 27 | 0,5 | 0,5239 | 0,0564 | **0,0915** |
| Gradient Boosting brut (tâche 56/58) | 27 | 0,5 | 0,5160 | 0,0513 | 0,000 |
| Gradient Boosting + class_weight (tâche 58) | 27 | 0,5 | 0,4916 | 0,0529 | 0,0608 |
| Gradient Boosting + seuil optimal (tâche 57) | 27 | 0,111 | 0,5160 | 0,0513 | 0,0879 |

**Modèle retenu pour l'explicabilité (tâches 59-60)** : Gradient Boosting (27 variables)
avec seuil optimal à 0,111, pour bénéficier de l'explicabilité par arbres (SHAP,
importance native) tout en gardant un rappel exploitable sur la classe grave.

---

## 5. Constat de performance

**Aucun modèle ne dépasse significativement le hasard** (ROC-AUC entre 0,49 et 0,53,
pour rappel 0,50 = tirage aléatoire). Fait notable : la régression logistique la plus
simple (4 variables, tâche 55) obtient le meilleur ROC-AUC de toutes les versions
testées — ajouter 23 variables supplémentaires et de la complexité (Gradient Boosting)
n'améliore pas la capacité de discrimination du modèle.

Ce résultat est **cohérent avec la tâche 49** (matrice de corrélations), qui avait déjà
montré qu'aucune variable disponible ne corrèle fortement avec la gravité. Il est
également cohérent avec l'analyse d'erreurs (tâche 60) : avec seulement 78 accidents
graves dans le jeu de test, la majorité passe inaperçue quel que soit le modèle.

---

## 6. Limites

- **Déséquilibre extrême des classes** (4,7 % de cas graves) : rend toute métrique
  basée sur la classe minoritaire (précision, F1, PR-AUC) très instable — un seul cas
  change la précision de plus d'un point.
- **Signal faible dans les variables disponibles** : la météo, le trafic et le contexte
  temporel expliquent le *volume* d'accidents (tâches 43-47) mais pas leur *gravité*.
  Les variables qui expliqueraient réellement la gravité (vitesse au choc, type de
  route, port de la ceinture/casque, type de véhicule) existent dans les données BAAC
  brutes mais ont été volontairement exclues pour éviter la fuite de données.
- **Périmètre restreint** : Paris intra-muros, une seule année (2024). Le modèle n'a
  aucune garantie de généraliser à d'autres villes, d'autres années, ou des conditions
  météo/trafic extrêmes non observées en 2024.
- **Split temporel court** : le Test ne couvre que ~2,5 mois (19/10 au 31/12/2024),
  une période qui peut avoir ses propres particularités saisonnières (fin d'année,
  jours fériés) non représentatives de l'année entière.

---

## 7. Biais potentiels

- **Biais géographique** : la population est rattachée au niveau commune (`com`), pas
  à l'adresse exacte — un biais socio-économique par arrondissement (le 75101 a une
  population résidente très faible face à un fort trafic de passage, ce qui gonfle
  artificiellement son taux d'accidents/habitant, cf. tâche 48) peut se répercuter
  dans les prédictions si la variable `population` est utilisée telle quelle.
- **Biais de couverture des capteurs trafic** : seulement ~51 % des accidents ont une
  mesure de trafic exploitable (couverture temporelle des capteurs, tâche 38), le
  reste étant imputé par la médiane — ça lisse artificiellement la variable `q_moyen`
  pour la moitié des cas.
- **Biais de rareté** : avec 78 cas graves en test, le modèle peut sur-apprendre les
  particularités de ces quelques cas plutôt qu'un vrai pattern généralisable.

---

## 8. Recommandation d'usage

**Ne pas déployer ce modèle pour de la décision opérationnelle** (priorisation
d'intervention, allocation de ressources, etc.) : sa capacité de discrimination est
trop proche du hasard pour être fiable dans ce contexte, et une fausse confiance dans
ses prédictions pourrait détourner des ressources de zones réellement à risque
(voir plutôt la tâche 48 — taux normalisés par commune — et la tâche 45 — zones à
risque géographiques — qui sont des analyses descriptives fiables, contrairement à ce
modèle prédictif).

**Usage recommandé** : support pédagogique et démonstrateur de méthodologie
(pipeline ML complet, anti-fuite de données, gestion du déséquilibre, explicabilité).

**Pistes d'amélioration pour une vraie mise en production** : intégrer des variables
au moment de l'accident lui-même dans un cadre méthodologique repensé (ex. prédire la
gravité *pendant* l'intervention plutôt qu'à l'avance), ou repositionner l'objectif
vers la prédiction du *risque d'accident* (fréquence, déjà bien traité en tâches 45/48)
plutôt que de sa *gravité*.