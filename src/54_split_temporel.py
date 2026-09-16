"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 54 — Split Apprentissage / Test (Découpage Temporel & Sans Leakage)
===============================================================================
"""

import sqlite3
import pandas as pd
import os
from pathlib import Path

# -----------------------------------------------------------------------------
# 1. INITIALISATION DES CHEMINS DYNAMIQUES
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
db_path = BASE_DIR / "data" / "mobilite_paris.db"

if not os.path.exists(db_path):
    raise FileNotFoundError(f"Base de données introuvable à l'emplacement : {db_path}")

# -----------------------------------------------------------------------------
# 2. CHARGEMENT ET TRI CHRONOLOGIQUE STRICT
# -----------------------------------------------------------------------------
conn = sqlite3.connect(db_path)

query = """
SELECT 
    f.id_fait, f.Num_Acc, f.id_usager, f.AAAAMMJJ, f.grav, m.RR, m.TM,
    CASE WHEN f.grav IN (2, 3) THEN 1 ELSE 0 END AS cible_grave,
    CAST(SUBSTR(f.AAAAMMJJ, 5, 2) AS INT) AS mois,
    CASE 
        WHEN m.RR = 0 THEN 'Temps Sec'
        WHEN m.RR > 0 AND m.RR <= 5 THEN 'Pluie Legere'
        WHEN m.RR > 5 THEN 'Pluie Forte'
        ELSE 'Inconnu'
    END AS condition_pluie
FROM FAIT_ACCIDENT_ENRICHI f
LEFT JOIN DIM_METEO m ON f.AAAAMMJJ = m.AAAAMMJJ
ORDER BY f.AAAAMMJJ ASC;
"""

df = pd.read_sql_query(query, conn)
conn.close()

# -----------------------------------------------------------------------------
# 3. SÉLECTION DES FEATURES ET CIBLE (AVANT TOUT TRAITEMENT)
# -----------------------------------------------------------------------------
features_list = ['condition_pluie', 'TM', 'mois']
X = df[features_list].copy()
y = df['cible_grave'].copy()

# -----------------------------------------------------------------------------
# 4. SPLIT TEMPOREL SUR LES DATES UNIQUES
# -----------------------------------------------------------------------------
dates_uniques = sorted(df["AAAAMMJJ"].unique())
index_limite = int(len(dates_uniques) * 0.80)
date_limite = dates_uniques[index_limite]

train_mask = df["AAAAMMJJ"] < date_limite

X_train, X_test = X[train_mask].copy(), X[~train_mask].copy()
y_train, y_test = y[train_mask].copy(), y[~train_mask].copy()

# -----------------------------------------------------------------------------
# 5. VÉRIFICATION D'INTÉGRITÉ : AUCUN ACCIDENT NE DOIT ÊTRE COUPÉ ENTRE TRAIN ET TEST
# -----------------------------------------------------------------------------
accidents_train = set(df[train_mask]["Num_Acc"])
accidents_test = set(df[~train_mask]["Num_Acc"])
accidents_dans_les_deux = accidents_train & accidents_test

# -----------------------------------------------------------------------------
# 6. IMPUTATION SANS DATA LEAKAGE (STATISTIQUES APPRISES SUR TRAIN SEUL)
# -----------------------------------------------------------------------------
if X_train['TM'].isnull().sum() > 0 or X_test['TM'].isnull().sum() > 0:
    mediane_tm_train = X_train['TM'].median()
    X_train['TM'] = X_train['TM'].fillna(mediane_tm_train)
    X_test['TM'] = X_test['TM'].fillna(mediane_tm_train)
    print(f"[INFO] Imputation réalisée : Médiane TM (Train uniquement) = {mediane_tm_train:.2f}°C")

# -----------------------------------------------------------------------------
# 7. CONTRÔLE ET AFFICHAGE POUR LE RAPPORT ET LA SOUTENANCE
# -----------------------------------------------------------------------------
date_debut_train = df[train_mask]['AAAAMMJJ'].min()
date_fin_train   = df[train_mask]['AAAAMMJJ'].max()
date_debut_test  = df[~train_mask]['AAAAMMJJ'].min()
date_fin_test    = df[~train_mask]['AAAAMMJJ'].max()

print("===================================================================")
print("             VALIDATION DU SPLIT TEMPOREL — TÂCHE 54              ")
print("===================================================================")
print(f"Nombre total d'usagers : {len(df)}")
print(f"Nombre de jours uniques: {len(dates_uniques)}")
print(f"Date pivot (début Test): {date_limite}")
print("-------------------------------------------------------------------")
if accidents_dans_les_deux:
    print(f"[ALERTE] {len(accidents_dans_les_deux)} accidents apparaissent à la fois dans Train et Test !")
else:
    print("[OK] Aucun accident n'est coupé entre Train et Test — intégrité confirmée.")
print("-------------------------------------------------------------------")
print(f" Ensemble Train (80% des jours) : {len(X_train)} usagers ({len(X_train)/len(df)*100:.1f}%)")
print(f"   ↳ Période : Du {date_debut_train} au {date_fin_train}")
print(f" Ensemble Test  (20% des jours) : {len(X_test)} usagers ({len(X_test)/len(df)*100:.1f}%)")
print(f"   ↳ Période : Du {date_debut_test} au {date_fin_test}")
print("-------------------------------------------------------------------")
print(" Taux de gravité (Cible = 1) :")
print(f"   ↳ Train : {y_train.mean()*100:.2f}%")
print(f"   ↳ Test  : {y_test.mean()*100:.2f}%")
print("===================================================================")
