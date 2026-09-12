# Rapport de qualité — ETL Phase 2

_Généré automatiquement le 2026-09-12 04:20_

## 1. Avant / après nettoyage

| Source | Lignes RAW | Colonnes RAW | Lignes CURATED | Colonnes CURATED | % lignes conservées |
|---|---|---|---|---|---|
| baac_caracteristiques | 54402 | 15 | N/A | N/A | N/A |
| baac_lieux | 70248 | 18 | N/A | N/A | N/A |
| baac_usagers | 125187 | 16 | N/A | N/A | N/A |
| baac_vehicules | 92678 | 11 | N/A | N/A | N/A |
| trafic | N/A | N/A | N/A | N/A | N/A |
| referentiel_geo | N/A | N/A | N/A | N/A | N/A |
| meteo | N/A | N/A | N/A | N/A | N/A |
| population | N/A | N/A | N/A | N/A | N/A |

## 2. Doublons

| Source | Doublons (toutes colonnes) | Doublons (clé métier) |
|---|---|---|
| baac_caracteristiques | N/A | N/A |
| baac_lieux | N/A | N/A |
| baac_usagers | N/A | N/A |
| baac_vehicules | N/A | N/A |
| trafic | N/A | N/A |
| referentiel_geo | N/A | N/A |
| meteo | N/A | N/A |
| population | N/A | N/A |

## 3. Taux de match entre sources

| Source A | Source B | Clé | % de A trouvé dans B | % de B trouvé dans A |
|---|---|---|---|---|
| baac_caracteristiques | baac_lieux | Num_Acc | N/A (fichier manquant) | N/A (fichier manquant) |
| baac_caracteristiques | meteo | AAAAMMJJ | N/A (fichier manquant) | N/A (fichier manquant) |
| trafic | referentiel_geo | iu_ac | N/A (fichier manquant) | N/A (fichier manquant) |
| baac_caracteristiques | referentiel_geo | GEO | N/A (fichier manquant) | N/A (fichier manquant) |

## 4. Notes / points d'attention

- Un taux de match bas peut venir d'un vrai non-recouvrement des données (ex : trafic non mesuré partout à Paris) ou d'un problème de clé (format de date différent, arrondi géographique trop fin/large, types non harmonisés). À vérifier au cas par cas avant d'interpréter comme une perte de qualité.
- Les cellules 'N/A (fichier manquant)' signalent une source pas encore nettoyée / sans clés construites : relancer nettoyer_*.py puis construire_cles_jointure.py, puis ce script.
