"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 46 — Analyse Croisée Météo × Gravité des Accidents
===============================================================================
Objectif Métier :
  Vérifier l'existence d'une relation statistique entre la pluviométrie (RR)
  et la gravité des accidents corporels subis par les usagers à Paris.

Résultats Statistiques Obtenus :
  - Effectif analysé : 9 132 usagers
  - Chi² (χ²)        : 4.3065
  - p-value          : 0.6353 (> 0.05 -> Indépendance statistique confirmée)
  - V de Cramér      : 0.0154 (Liaison quasi-nulle)

Interprétation Métier :
  Il n'y a pas d'association significative entre la météo et la gravité.
  La proportion de blessés graves/décès reste stable (4.20% à 4.46%) quelle
  que soit la météo (comportement d'adaptation des conducteurs en milieu urbain).
===============================================================================
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency
import os
from pathlib import Path

# -----------------------------------------------------------------------------
# CONFIGURATION DES CHEMINS DYNAMIQUES (PORTABILITÉ MULTI-UTILISATEURS)
# -----------------------------------------------------------------------------
# Définition du dossier racine du projet (1 niveau au-dessus de /src)
BASE_DIR = Path(__file__).resolve().parent.parent

# Chemins absolus vers les fichiers de données et d'export
db_path = BASE_DIR / "data" / "mobilite_paris.db"
img_path = BASE_DIR / "data" / "analyse_meteo_gravite.png"

# Vérification de sécurité avant exécution
if not os.path.exists(db_path):
    raise FileNotFoundError(f"Erreur : La base de données est introuvable à l'adresse : {db_path}")

# -----------------------------------------------------------------------------
# 1. CONNEXION À LA BASE DE DONNÉES SQLITE
# -----------------------------------------------------------------------------
conn = sqlite3.connect(db_path)

# -----------------------------------------------------------------------------
# 2. EXTRACTION ET FORMATAGE DES DONNÉES (SQL JOIN)
# -----------------------------------------------------------------------------
query = """
SELECT 
    f.id_fait,
    f.Num_Acc,
    f.AAAAMMJJ,
    f.grav,
    m.RR,
    m.TM,

    -- Discrétisation des précipitations (RR en mm) en 3 catégories opérationnelles
    CASE 
        WHEN m.RR = 0 THEN 'Temps Sec (0 mm)'
        WHEN m.RR > 0 AND m.RR <= 5 THEN 'Pluie Léger (0-5 mm)'
        WHEN m.RR > 5 THEN 'Pluie Forte (>5 mm)'
        ELSE 'Inconnu'
    END AS condition_pluie,

    -- Mappage des codes BAAC de gravité (1 à 4) vers des libellés explicites
    CASE 
        WHEN f.grav = 1 THEN 'Indemne'
        WHEN f.grav = 2 THEN 'Tué'
        WHEN f.grav = 3 THEN 'Blessé Hospitalisé'
        WHEN f.grav = 4 THEN 'Blessé Léger'
        ELSE 'Inconnu'
    END AS libel_gravite,

    -- Regroupement binaire pour la modélisation / visualisation synthétique
    CASE 
        WHEN f.grav IN (2, 3) THEN 'Grave / Décès'
        WHEN f.grav IN (1, 4) THEN 'Léger / Indemne'
        ELSE 'Autre'
    END AS classe_gravite

FROM FAIT_ACCIDENT f
JOIN DIM_METEO m ON f.AAAAMMJJ = m.AAAAMMJJ;
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f"Total usagers analysés : {len(df)}")

# -----------------------------------------------------------------------------
# 3. CONSTRUCTION DES TABLES DE CONTINGENCE
# -----------------------------------------------------------------------------
ct_abs = pd.crosstab(df['condition_pluie'], df['libel_gravite'], margins=True, margins_name="Total")
ct_pct = pd.crosstab(df['condition_pluie'], df['libel_gravite'], normalize='index') * 100

print("\n=== TABLE DE CONTINGENCE (EFFECTIFS) ===")
print(ct_abs)

print("\n=== RÉPARTITION EN POURCENTAGE (%) PAR CONDITION MÉTÉO ===")
print(ct_pct.round(2))

# -----------------------------------------------------------------------------
# 4. INFÉRENCE STATISTIQUE : TEST DU CHI-DEUX & V DE CRAMÉR
# -----------------------------------------------------------------------------
ct_stat = pd.crosstab(df['condition_pluie'], df['libel_gravite'])
chi2, p_val, dof, expected = chi2_contingency(ct_stat)

n = ct_stat.sum().sum()
v_cramer = np.sqrt(chi2 / (n * (min(ct_stat.shape) - 1)))

print("\n=== TEST STATISTIQUE CHI-DEUX & V DE CRAMÉR ===")
print(f"Statistique Chi2 : {chi2:.4f}")
print(f"p-value          : {p_val:.4e}")
print(f"V de Cramér      : {v_cramer:.4f}")

# -----------------------------------------------------------------------------
# 5. VISUALISATION DES RÉSULTATS ET SAUVEGARDE
# -----------------------------------------------------------------------------
plt.figure(figsize=(10, 5))
sns.countplot(data=df, x='condition_pluie', hue='classe_gravite', palette='Set2')

plt.title('Répartition de la Gravité des Accidents selon la Météo')
plt.xlabel('Condition Météorologique')
plt.ylabel("Nombre d'usagers")
plt.legend(title='Classe Gravité')
plt.tight_layout()

# Sauvegarde avec le chemin dynamique Path
plt.savefig(img_path)
plt.show()