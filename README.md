# Projet Data & IA — Mobilité & Sécurité Routière (Paris)

Projet collectif (équipe de 9) pour l'Agence Territoriale Mobilité & Sécurité (ATMS, fictive) :
comprendre les facteurs associés aux accidents corporels à Paris et estimer le risque de
gravité d'un accident à partir du contexte routier, temporel, météorologique et territorial.

## Territoire retenu

Paris — justifié par la richesse de son historique de données trafic (capteurs permanents
depuis 2010) et la disponibilité confirmée des 5 sources nécessaires (voir `catalogue/Catalogue_final.xlsx`).

## Suivi du projet

- `PROGRESSION.md` (racine du dépôt) : avancement des 7 grandes phases, vue d'ensemble rapide
- `docs/SUIVI_PROJET_LIEN.md` : lien vers le suivi détaillé, partagé et modifiable par toute l'équipe sur OneDrive

## Architecture du dépôt
├── PROGRESSION.md → suivi des 7 phases (vue rapide)
├── catalogue/
│ └── Catalogue_final.xlsx → catalogue de sourcing (source unique de référence)
├── data/
│ ├── raw/ → données brutes horodatées, non versionnées (voir .gitignore)
│ ├── curated/ → données nettoyées (Phase 2, en cours)
│ └── sample/ → échantillons légers versionnés, pour consultation rapide
├── docs/
│ ├── cahier_des_charges.pdf
│ ├── Feuille_de_route_projet.pdf
│ └── SUIVI_PROJET_LIEN.md → lien vers le suivi détaillé (OneDrive)
├── src/ → scripts d'acquisition, de nettoyage et utilitaires
├── notebooks/ → analyses (à venir, Phase 4-5)
├── sql/ → schéma de base de données (à venir, Phase 3)
└── dashboard/ → dashboard final (à venir, Phase 4)


## Prérequis / installation

- Python 3.12+
- Dépendances :
python -m pip install requests pandas

- **7-Zip** requis pour extraire manuellement 2 archives dont la méthode de compression
  n'est pas supportée par la librairie Python `zipfile` (voir Limites ci-dessous) :
  https://www.7-zip.org/

## Ordre d'exécution (acquisition des données brutes)

Depuis le dossier `src/`, exécuter dans cet ordre (indépendants les uns des autres) :
python telecharger_baac.py
python telecharger_trafic.py
python telecharger_referentiel_geo.py
python telecharger_meteo.py
python telecharger_population.py


Chaque script détecte automatiquement la racine du projet (via le dossier `.git`) et crée
son arborescence dans `data/raw/<source>/<date_du_jour>/`. L'exécution est journalisée dans
`src/logs/<nom_du_script>.log`.

Pour créer un échantillon léger (versionné sur GitHub) : `python creer_echantillon.py`.

## Nettoyage des données (Phase 2)

Depuis `src/`, chaque script `nettoyer_*.py` lit la version la plus récente des données RAW
et produit des fichiers propres dans `data/curated/<source>/` :
python nettoyer_baac.py
python nettoyer_trafic.py
python nettoyer_population.py


## Sources de données

Résumé — détail complet dans `catalogue/Catalogue_final.xlsx` :

| Source | Producteur | Période | Méthode |
|---|---|---|---|
| BAAC (accidents) | ONISR / Ministère de l'Intérieur | 2020-2024 | API JSON + téléchargement scripté |
| Trafic routier | Ville de Paris | 2020-2024 | Téléchargement scripté (ZIP/TXT hebdo) |
| Référentiel géographique | Ville de Paris | Statique | API REST (Opendatasoft, pagination) |
| Météo (dept. 75) | Météo-France | 1950-2024 | Téléchargement scripté |
| Population de référence | INSEE | 2023 | Téléchargement scripté (ZIP) |

## Limites connues (à date)

- Noms de fichiers BAAC incohérents selon les années (`caracteristiques-2020`,
  `caract-2023/2024`, `carcteristiques-2021/2022` — faute de frappe côté source) et
  `vehicules-immatricule` (singulier, 2024) vs `vehicules-immatricules` (pluriel, 2020-2023).
- Archives trafic 2021 et 2023 : méthode de compression non supportée par `zipfile`,
  extraction manuelle via 7-Zip nécessaire.
- Population : millésime 2023 utilisé comme approximation pour 2024 (dernière donnée
  officielle disponible, écart jugé négligeable sur un an).
- Encodage des fichiers BAAC corrigé en Phase 2 (`latin-1` pour les fichiers BAAC
  standards ; le fichier véhicules immatriculés nécessitait `utf-8`, non résolu — voir
  point suivant).
- Fichier `vehicules-immatricule-baac-2024` exclu du pipeline : sa clé de jointure
  (`Id_accident`, ex. "67 230 442") ne correspond à aucun format compatible avec `Num_Acc`
  des autres fichiers BAAC (ex. 202400000011), et aucune table de correspondance officielle
  n'a été trouvée sur data.gouv.fr. Le fichier `vehicules` standard (colonne `catv`) fournit
  déjà une catégorisation suffisante des véhicules impliqués.
- Fichier `lieux` : plusieurs lignes par accident lorsque celui-ci s'est produit à une
  intersection (2 voies enregistrées séparément) — traité en gardant la première voie et
  en ajoutant un indicateur booléen `intersection` (64 % des accidents parisiens 2024
  concernés).
- Référentiel géographique : coordonnées à vérifier/reprojeter si nécessaire en Phase 2.

## Journal de contribution

Voir `docs/SUIVI_PROJET_LIEN.md` (fichier partagé sur OneDrive) pour la répartition des
tâches et l'avancement par membre.

## État d'avancement

- [x] Phase 0 — Sourcing & faisabilité
- [x] Phase 1 — Acquisition & stockage RAW
- [ ] Phase 2 — ETL & qualité (en cours — BAAC terminé)
- [ ] Phase 3 — Intégration & modèle de données
- [ ] Phase 4 — Analyse & data visualisation
- [ ] Phase 5 — Intelligence artificielle
- [ ] Phase 6 — Restitution & reproductibilité