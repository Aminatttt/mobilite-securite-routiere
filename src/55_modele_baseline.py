"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 55 — Modèle Baseline (Régression Logistique Météo/Saison)
===============================================================================
Objectif Métier :
  1. Entraîner un premier modèle de référence (Baseline) sur les facteurs
     météorologiques, temporels et de luminosité.
  2. Éviter toute redondance exacte de variables (conservation de RR en mm,
     retrait de condition_pluie qui en est dérivée).
  3. Securiser le One-Hot Encoding de la saison via des catégories fixes
     (pd.Categorical) pour garantir la parfaite concordance des colonnes.
  4. Appliquer strictement les transformations (imputation des médianes et
     normalisation StandardScaler) ajustées sur Train uniquement.
  5. Évaluer le modèle de manière neutre sur le Test (ROC-AUC, Seuil 0.5,
     Matrice de confusion et Rapport de classification).
===============================================================================
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    confusion_matrix,
    classification_report
)

# -----------------------------------------------------------------------------
# 1. INITIALISATION ET VÉRIFICATION DE LA BASE DE DONNÉES
# -----------------------------------------------------------------------------
# Définition dynamique du chemin d'accès à la base SQLite pour garantir la 
# portabilité du script sur n'importe quel système d'exploitation.
BASE_DIR = Path(__file__).resolve().parent.parent
db_path = BASE_DIR / "data" / "mobilite_paris.db"

if not os.path.exists(db_path):
    raise FileNotFoundError(f"Base de données introuvable à l'emplacement : {db_path}")

conn = sqlite3.connect(db_path)

# Détection dynamique de la table source (Fallback de sécurité si table non enrichie)
tables_existantes = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].tolist()
table_source = "FAIT_ACCIDENT_ENRICHI" if "FAIT_ACCIDENT_ENRICHI" in tables_existantes else "FAIT_ACCIDENT"

# -----------------------------------------------------------------------------
# 2. CHARGEMENT DES DONNÉES ET FEATURE ENGINEERING EN SQL
# -----------------------------------------------------------------------------
# Extraction des variables explicatives non redondantes :
# - Conservation de RR (mm) au lieu de condition_pluie (évite la redondance exacte)
# - Binary indicator 'condition_lum' dérivé du champ 'lum'
# - Découpage en 4 saisons calendaires à partir du mois
query = f"""
SELECT 
    f.Num_Acc,
    f.AAAAMMJJ,
    f.grav,
    f.lum,
    m.TM,
    m.RR,
    
    -- Variable binaire de luminosité (1 = Obscurité / Nuit, 0 = Plein jour)
    -- Note : En SQL, un NULL éventuel dans 'lum' retombe automatiquement dans ELSE 0
    CASE 
        WHEN f.lum IN (2, 3, 4, 5) THEN 1 
        ELSE 0 
    END AS condition_lum,
    
    -- Catégorisation de la saisonnalité à partir de la date (AAAAMMJJ)
    CASE 
        WHEN CAST(SUBSTR(CAST(f.AAAAMMJJ AS TEXT), 5, 2) AS INT) IN (12, 1, 2) THEN 'Hiver'
        WHEN CAST(SUBSTR(CAST(f.AAAAMMJJ AS TEXT), 5, 2) AS INT) IN (3, 4, 5) THEN 'Printemps'
        WHEN CAST(SUBSTR(CAST(f.AAAAMMJJ AS TEXT), 5, 2) AS INT) IN (6, 7, 8) THEN 'Ete'
        ELSE 'Automne'
    END AS saison

FROM {table_source} f
LEFT JOIN DIM_METEO m ON CAST(f.AAAAMMJJ AS TEXT) = CAST(m.AAAAMMJJ AS TEXT)
ORDER BY f.AAAAMMJJ ASC;
"""

df = pd.read_sql_query(query, conn)
conn.close()

# Encodage de la variable Cible Binaire : 1 = Grave (Tué = 2, Hospitalisé = 3), 0 = Léger
df["gravite_bin"] = df["grav"].isin([2, 3]).astype(int)

# -----------------------------------------------------------------------------
# 3. CONTRÔLE D'INTÉGRITÉ STRICT (TÂCHE 54)
# -----------------------------------------------------------------------------
# Vérification qu'aucun accident (Num_Acc) ne chevauche plusieurs dates
controle_dates_accident = df.groupby("Num_Acc")["AAAAMMJJ"].nunique()
nb_accidents_multi_dates = (controle_dates_accident > 1).sum()

if nb_accidents_multi_dates > 0:
    raise ValueError(f"Erreur d'intégrité : {nb_accidents_multi_dates} accidents s'étalent sur plusieurs dates !")

# -----------------------------------------------------------------------------
# 4. SPLIT TEMPOREL SUR LES DATES UNIQUES
# -----------------------------------------------------------------------------
# Extraction des dates uniques pour un découpage 80% Train / 20% Test sur le calendrier
jours_uniques = np.sort(df["AAAAMMJJ"].unique())
split_idx_jour = int(len(jours_uniques) * 0.80)
date_pivot = jours_uniques[split_idx_jour]

# Création des masques de découpage temporel
train_mask = df["AAAAMMJJ"] < date_pivot
test_mask = df["AAAAMMJJ"] >= date_pivot

# -----------------------------------------------------------------------------
# 5. ENCODAGE ONE-HOT SÉCURISÉ (AVANT SPLIT VIA CATEGORICAL)
# -----------------------------------------------------------------------------
features_base = ["TM", "RR", "condition_lum"]

# Imposition d'une liste fixe de catégories pour la saison.
# Cela garantit que 'Automne' sera TOUJOURS la catégorie supprimée (drop_first=True),
# évitant tout décalage d'encodage entre le Train et le Test.
df["saison"] = pd.Categorical(
    df["saison"], categories=["Automne", "Ete", "Hiver", "Printemps"]
)

# Génération des colonnes binarisées sur l'ensemble global
df_encoded = pd.get_dummies(
    df[features_base + ["saison"]], columns=["saison"], drop_first=True
)

# Séparation des caractéristiques (X) et de la cible (y) en Train / Test
X_train = df_encoded[train_mask].copy()
X_test = df_encoded[test_mask].copy()

y_train = df.loc[train_mask, "gravite_bin"].copy()
y_test = df.loc[test_mask, "gravite_bin"].copy()

# -----------------------------------------------------------------------------
# 6. IMPUTATION ET STANDARDISATION STRICTE (ANTI-DATA LEAKAGE)
# -----------------------------------------------------------------------------
# A. IMPUTATION : Calcul des médianes EXCLUSIVEMENT sur X_train
tm_mediane_train = X_train["TM"].median()
rr_mediane_train = X_train["RR"].median()

X_train["TM"] = X_train["TM"].fillna(tm_mediane_train)
X_train["RR"] = X_train["RR"].fillna(rr_mediane_train)

X_test["TM"] = X_test["TM"].fillna(tm_mediane_train)
X_test["RR"] = X_test["RR"].fillna(rr_mediane_train)

# B. NORMALISATION : Centrage-réduction calibré STRICTEMENT sur X_train
scaler = StandardScaler()

# Fit + Transform sur Train / Transform uniquement sur Test
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# -----------------------------------------------------------------------------
# 7. ENTRAÎNEMENT DU MODÈLE BASELINE (RÉGRESSION LOGISTIQUE)
# -----------------------------------------------------------------------------
# Configuration de la régression logistique avec gestion du déséquilibre de classe
model = LogisticRegression(
    class_weight="balanced", 
    max_iter=1000, 
    random_state=42
)

# Fit du modèle sur les données d'entraînement normalisées
model.fit(X_train_scaled, y_train)

# -----------------------------------------------------------------------------
# 8. ÉVALUATION STRICTE SUR LE JEU DE TEST (SANS LEAKAGE DE DÉCISION)
# -----------------------------------------------------------------------------
# Calcul des probabilités de la classe grave (1) sur l'ensemble Test
y_probs_test = model.predict_proba(X_test_scaled)[:, 1]

# Calcul du score ROC-AUC (métrique globale indépendante du seuil)
auc_score = roc_auc_score(y_test, y_probs_test)

# Application du seuil standard neutre de 0.5 (sans ajustement sur Test)
seuil_standard = 0.5
y_pred_test = (y_probs_test >= seuil_standard).astype(int)

# -----------------------------------------------------------------------------
# 9. AFFICHAGE DES RÉSULTATS ET BILAN DE PERFORMANCE
# -----------------------------------------------------------------------------
date_debut_train = df[train_mask]['AAAAMMJJ'].min()
date_fin_train   = df[train_mask]['AAAAMMJJ'].max()
date_debut_test  = df[test_mask]['AAAAMMJJ'].min()
date_fin_test    = df[test_mask]['AAAAMMJJ'].max()

print("===================================================================")
print("     ÉVALUATION DU MODÈLE BASELINE (RÉGRESSION LOGISTIQUE) — T55   ")
print("===================================================================")
print(f"Table source utilisée   : {table_source}")
print(f"Nombre total d'usagers  : {len(df)}")
print(f"Date pivot (début Test) : {date_pivot}")
print("-------------------------------------------------------------------")
print(f" Partition Train : {len(X_train)} lignes ({len(X_train)/len(df)*100:.1f}%) | Du {date_debut_train} au {date_fin_train}")
print(f" Partition Test  : {len(X_test)} lignes ({len(X_test)/len(df)*100:.1f}%) | Du {date_debut_test} au {date_fin_test}")
print("-------------------------------------------------------------------")
print(f" Score ROC-AUC (Test) : {auc_score:.4f}")
print("-------------------------------------------------------------------")

cm = confusion_matrix(y_test, y_pred_test)
tn, fp, fn, tp = cm.ravel()

print(f" Matrice de Confusion (Seuil de décision = {seuil_standard}) :")
print(f"   ↳ [TN={tn:5d}  |  FP={fp:5d}]  (Légers Réels)")
print(f"   ↳ [FN={fn:5d}  |  TP={tp:5d}]  (Graves Réels)")
print("-------------------------------------------------------------------")
print(" Rapport de Classification Détaillé :")
print(classification_report(y_test, y_pred_test, target_names=["Léger (0)", "Grave (1)"]))
print("===================================================================")

"""
===============================================================================
                       INTERPRÉTATION DES RÉSULTATS (TÂCHE 55)
===============================================================================

1. Analyse des Métriques Principales :
--------------------------------------
* Score ROC-AUC (0.5345) :
  - Définition : La courbe ROC-AUC mesure la capacité globale du modèle à séparer
    les usagers légers des usagers graves (0.50 = hasard, 1.00 = parfait).
  - Interprétation : Un score de 0.5345 indique que la météo, la température et
    la saisonnalité ont un pouvoir prédictif très faible lorsqu'elles sont utilisées
    seules. Cela confirme l'hypothèse (Tâche 46) : la météo influe sur le volume
    des accidents, mais très peu sur leur gravité brute.

* Rappel / Recall sur les cas Graves (0.74 soit 74%) :
  - Définition : Proportion d'accidents graves réels correctement détectés.
  - Interprétation : Le modèle a détecté 58 accidents graves sur 78 (FN = 20).
    L'option class_weight='balanced' force efficacement le modèle à prioriser
    la classe minoritaire (les graves).

* Précision sur les cas Graves (0.05 soit 5%) :
  - Définition : Pourcentage de vrais graves parmi les alerte "Grave" lancées.
  - Interprétation : Sur 1 103 individus prédits comme graves, seuls 58 l'étaient
    réellement (1 045 faux positifs). Le modèle est donc très prudent et génère
    un nombre élevé de fausses alertes.

2. Matrice de Confusion (Seuil = 0.5) :
---------------------------------------
   [ TN = 490  |  FP = 1045 ]
   [ FN =  20  |  TP =   58 ]

  - Vrais Négatifs (TN = 490)  : Accidents légers correctement classés légers.
  - Faux Positifs (FP = 1045)  : Accidents légers prédits graves (fausses alertes).
  - Faux Négatifs (FN = 20)    : Accidents graves râtés (prédits comme légers).
  - Vrais Positifs (TP = 58)   : Accidents graves correctement identifiés.

3. Bilan Métier & Perspective :
-------------------------------
  - Rôle de Baseline validé : Fixe le score de référence minimal (AUC ≈ 0.53).
  - Nécessité des variables avancées : Pour améliorer la précision et le score
    ROC-AUC, l'intégration des variables d'infrastructure (type de voie, vitesse),
    de véhicule et de comportement usager sera indispensable dans les prochaines tâches.
===============================================================================
"""