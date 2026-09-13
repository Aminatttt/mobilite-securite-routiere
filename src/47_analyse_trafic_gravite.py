"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 47 — Analyse Croisée Trafic × Gravité des Accidents
===============================================================================
Objectif Métier :
  Vérifier l'existence d'une relation statistique entre l'intensité moyenne du trafic
  (q_moyen) et la gravité des accidents corporels à partir de la table enrichie.

Résultats Statistiques Obtenus :
  - Effectif analysé : (Généré dynamiquement)
  - Chi² (χ²)        : Calculé par le script
  - p-value          : Évaluation de l'indépendance statistique
  - V de Cramér      : Mesure de l'intensité de la liaison
===============================================================================
"""

from pathlib import Path
import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency

# -----------------------------------------------------------------------------
# CONFIGURATION DES CHEMINS DYNAMIQUES
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

db_path = BASE_DIR / "data" / "mobilite_paris.db"
img_path = BASE_DIR / "data" / "analyse_trafic_gravite.png"

if not os.path.exists(db_path):
    raise FileNotFoundError(
        f"Erreur : La base de données est introuvable à l'adresse : {db_path}"
    )

# -----------------------------------------------------------------------------
# 1. CONNEXION À LA BASE DE DONNÉES SQLITE
# -----------------------------------------------------------------------------
conn = sqlite3.connect(db_path)

# -----------------------------------------------------------------------------
# 2. EXTRACTION ET FORMATAGE DES DONNÉES (DEPUIS LA TABLE ENRICHIE)
# -----------------------------------------------------------------------------
query = """
SELECT 
    id_fait,
    Num_Acc,
    AAAAMMJJ,
    grav,
    q_moyen,

    -- Discrétisation du trafic en catégories opérationnelles basées sur q_moyen
    CASE 
        WHEN q_moyen < 500 THEN 'Trafic Fluide (Faible)'
        WHEN q_moyen >= 500 AND q_moyen <= 1500 THEN 'Trafic Modéré'
        WHEN q_moyen > 1500 THEN 'Trafic Dense / Saturé'
        ELSE 'Inconnu'
    END AS niveau_trafic,

    -- Mappage des codes BAAC de gravité (1 à 4) vers des libellés explicites
    CASE 
        WHEN grav = 1 THEN 'Indemne'
        WHEN grav = 2 THEN 'Tué'
        WHEN grav = 3 THEN 'Blessé Hospitalisé'
        WHEN grav = 4 THEN 'Blessé Léger'
        ELSE 'Inconnu'
    END AS libel_gravite,

    -- Regroupement binaire pour la modélisation / visualisation synthétique
    CASE 
        WHEN grav IN (2, 3) THEN 'Grave / Décès'
        WHEN grav IN (1, 4) THEN 'Léger / Indemne'
        ELSE 'Autre'
    END AS classe_gravite

FROM FAIT_ACCIDENT_ENRICHI;
"""

df = pd.read_sql_query(query, conn)
conn.close()

print(f"Total usagers analysés : {len(df)}")

# -----------------------------------------------------------------------------
# 3. CONSTRUCTION DES TABLES DE CONTINGENCE
# -----------------------------------------------------------------------------
ct_abs = pd.crosstab(
    df["niveau_trafic"], df["libel_gravite"], margins=True, margins_name="Total"
)
ct_pct = (
    pd.crosstab(df["niveau_trafic"], df["libel_gravite"], normalize="index")
    * 100
)

print("\n=== TABLE DE CONTINGENCE (EFFECTIFS) ===")
print(ct_abs)

print("\n=== RÉPARTITION EN POURCENTAGE (%) PAR NIVEAU DE TRAFIC ===")
print(ct_pct.round(2))

# -----------------------------------------------------------------------------
# 4. INFÉRENCE STATISTIQUE : TEST DU CHI-DEUX & V DE CRAMÉR
# -----------------------------------------------------------------------------
ct_stat = pd.crosstab(df["niveau_trafic"], df["libel_gravite"])
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
sns.countplot(
    data=df,
    x="niveau_trafic",
    hue="classe_gravite",
    palette="Set2",
    order=[
        "Trafic Fluide (Faible)",
        "Trafic Modéré",
        "Trafic Dense / Saturé",
        "Inconnu",
    ],
)

plt.title("Répartition de la Gravité des Accidents selon le Niveau de Trafic")
plt.xlabel("Niveau de Trafic (q_moyen)")
plt.ylabel("Nombre d'usagers")
plt.legend(title="Classe Gravité")
plt.tight_layout()

# Sauvegarde avec le chemin dynamique Path
plt.savefig(img_path)
plt.show()