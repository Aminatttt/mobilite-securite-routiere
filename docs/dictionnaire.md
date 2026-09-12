# 📖 DICTIONNAIRE DE DONNÉES

**Projet : Data & IA — Mobilité & Sécurité Routière (Paris)**
*Ce document recense les variables conservées après l'ETL pour l'intégration en base de données et la modélisation.*

## 1. 🔑 Clés de jointure et Identifiants
| Nom de la variable | Source | Type SQL | Description | Format / Modalités |
| :--- | :--- | :--- | :--- | :--- |
| `Num_Acc` | BAAC | `VARCHAR` | Identifiant unique de l'accident (Clé Primaire) | Ex : `202300000001` |
| `AAAAMMJJ` | Toutes | `VARCHAR` | Date formatée pour les jointures temporelles | Ex : `20230514` |
| `GEO` | Toutes | `VARCHAR` | Code INSEE de l'arrondissement parisien | Ex : `75101` à `75120` |
| `iu_ac` | Trafic | `VARCHAR` | Identifiant unique du tronçon routier | Ex : `1234_5678` |

## 2. 🚗 Données Accidents (BAAC nettoyée)
| Nom de la variable | Source | Type SQL | Description | Format / Modalités |
| :--- | :--- | :--- | :--- | :--- |
| `date_heure` | BAAC | `TIMESTAMP`| Date et heure exactes de l'accident | `YYYY-MM-DD HH:MM:SS` |
| `latitude` | BAAC | `FLOAT` | Coordonnée GPS (Latitude en WGS84) | Décimal |
| `longitude` | BAAC | `FLOAT` | Coordonnée GPS (Longitude en WGS84) | Décimal |
| `lum` | BAAC | `INTEGER` | Conditions d'éclairage | 1=Jour, 2=Crépuscule, 3=Nuit... |
| `atm` | BAAC | `INTEGER` | Conditions atmosphériques | 1=Normale, 2=Pluie, 3=Brouillard... |
| `surf` | BAAC | `INTEGER` | État de la surface de la route | 1=Normale, 2=Mouillée... |
| `nb_vehicules` | BAAC | `INTEGER` | Nombre de véhicules impliqués | Numérique |
| `grav_cible` | BAAC | `INTEGER` | **Cible IA (Phase 5)** : Gravité max de l'accident | 0=Non grave, 1=Grave |

## 3. 🚦 Données Trafic (Historique)
| Nom de la variable | Source | Type SQL | Description | Format / Modalités |
| :--- | :--- | :--- | :--- | :--- |
| `q_debit` | Trafic | `FLOAT` | Débit horaire (véhicules/heure) | Numérique |
| `k_taux_occ` | Trafic | `FLOAT` | Taux d'occupation de la chaussée | 0 à 100% |
| `etat_trafic` | Trafic | `VARCHAR` | Catégorisation de la fluidité | Fluide, Dense, Saturé, Bloqué |

## 4. 🌦️ Données Météo (Station Paris)
| Nom de la variable | Source | Type SQL | Description | Format / Modalités |
| :--- | :--- | :--- | :--- | :--- |
| `temp_moy` | Météo | `FLOAT` | Température moyenne journalière | En °C |
| `precip_mm` | Météo | `FLOAT` | Cumul des précipitations | En mm |
| `rafale_max` | Météo | `FLOAT` | Vitesse max des rafales de vent | En km/h |

## 5. 👥 Données Population (INSEE)
| Nom de la variable | Source | Type SQL | Description | Format / Modalités |
| :--- | :--- | :--- | :--- | :--- |
| `pop_totale` | INSEE | `INTEGER` | Population résidente dans l'arrondissement | Numérique |
| `densite_pop` | INSEE | `FLOAT` | Densité de population de la zone | Hab/km² |