# Projet Data & IA — Mobilité & Sécurité Routière (Paris)

Projet collectif (équipe de 9) pour l'Agence Territoriale Mobilité & Sécurité (ATMS, fictive) :
comprendre les facteurs associés aux accidents corporels à Paris et estimer le risque de
gravité d'un accident à partir du contexte routier, temporel, météorologique et territorial.

## Territoire retenu
Paris — justifié par la richesse de son historique de données trafic (capteurs permanents
depuis 2010) et la disponibilité confirmée des 5 sources nécessaires (voir `PROJET/Catalogue_final.xlsx`).

## Architecture du dépôt

├── PROJET/ → catalogue de sourcing
├── data/
│ ├── raw/ → données brutes horodatées, non versionnées (voir .gitignore)
│ ├── curated/ → données nettoyées (Phase 2, à venir)
│ └── sample/ → échantillons légers versionnés, pour consultation rapide
├── docs/ → suivi de projet, cahier des charges
├── src/ → scripts d'acquisition et utilitaires
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


Chaque script crée automatiquement son arborescence dans `data/raw/<source>/<date_du_jour>/`
et journalise son exécution dans `src/logs/<nom_du_script>.log`.

Pour créer un échantillon léger (versionné sur GitHub) : `python creer_echantillon.py`
(adapter les chemins horodatés en haut du script si besoin).

## Sources de données

Résumé — détail complet dans `PROJET/Catalogue_final.xlsx` :

| Source | Producteur | Période | Méthode |
|---|---|---|---|
| BAAC (accidents) | ONISR / Ministère de l'Intérieur | 2020-2024 | API JSON + téléchargement scripté |
| Trafic routier | Ville de Paris | 2020-2024 | Téléchargement scripté (ZIP/TXT hebdo) |
| Référentiel géographique | Ville de Paris | Statique | API REST (Opendatasoft, pagination) |
| Météo (dept. 75) | Météo-France | 1950-2024 | Téléchargement scripté |
| Population de référence | INSEE | 2023 | Téléchargement scripté (ZIP) |

## Limites connues (à date — Phase 1 terminée)

- Noms de fichiers BAAC incohérents selon les années (`caracteristiques-2020`,
  `caract-2023/2024`, `carcteristiques-2021/2022` — faute de frappe côté source) et
  `vehicules-immatricule` (singulier, 2024) vs `vehicules-immatricules` (pluriel, 2020-2023).
- Archives trafic 2021 et 2023 : méthode de compression non supportée par `zipfile`,
  extraction manuelle via 7-Zip nécessaire.
- Population : millésime 2023 utilisé comme approximation pour 2024 (dernière donnée
  officielle disponible, écart jugé négligeable sur un an).
- Encodage des fichiers BAAC à vérifier/corriger en Phase 2 (accents mal interprétés
  observés sur certains fichiers).
- Référentiel géographique : coordonnées à reprojeter (Lambert 93 → WGS84) en Phase 2.

## Journal de contribution

Voir `docs/SUIVI_PROJET.xlsx` pour la répartition des tâches et l'avancement par membre.

## État d'avancement

- [x] Phase 0 — Sourcing & faisabilité
- [x] Phase 1 — Acquisition & stockage RAW
- [ ] Phase 2 — ETL & qualité
- [ ] Phase 3 — Intégration & modèle de données
- [ ] Phase 4 — Analyse & data visualisation
- [ ] Phase 5 — Intelligence artificielle
- [ ] Phase 6 — Restitution & reproductibilité
