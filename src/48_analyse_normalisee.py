"""
===============================================================================
TÂCHE 48 — ANALYSE NORMALISÉE (accidents / 100 000 habitants)
===============================================================================
Objectif : comparer les arrondissements/communes non pas en nombre brut
d'accidents (biaisé par la taille de la population) mais en taux normalisé,
pour identifier les zones réellement les plus dangereuses par habitant.

Entrée  : data/mobilite_paris.db -> table FAIT_ACCIDENT_ENRICHI
          (contient 'com' et 'population', propagés en tâches 36-38)
Sorties : data/curated/resultats/tache_48/
              taux_accidents_pour_100k.csv
              taux_accidents_pour_100k.png
===============================================================================
"""

from pathlib import Path
import sqlite3

import pandas as pd
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------
# CHEMINS
# -----------------------------------------------------------------------
DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT

DB_PATH = RACINE_PROJET / "data" / "mobilite_paris.db"
DOSSIER_RESULTATS = RACINE_PROJET / "data" / "curated" / "resultats" / "tache_48"
DOSSIER_RESULTATS.mkdir(parents=True, exist_ok=True)


def realiser_analyse_normalisee():
    print("=" * 80)
    print("TÂCHE 48 — ANALYSE NORMALISÉE (accidents / 100 000 habitants)")
    print("=" * 80)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        """
        SELECT Num_Acc, com, population, grav
        FROM FAIT_ACCIDENT_ENRICHI
        """,
        conn,
    )
    conn.close()

    print(f"\n[INFO] Lignes chargées (grain usager) : {len(df):,}")

    df["grav"] = pd.to_numeric(df["grav"], errors="coerce")
    df["population"] = pd.to_numeric(df["population"], errors="coerce")

    # -------------------------------------------------------------------
    # Passage au grain ACCIDENT (un accident = une ligne), gravité max retenue
    # Codage BAAC : 2 = tué, 3 = blessé hospitalisé, 4 = blessé léger, 1 = indemne
    # -------------------------------------------------------------------
    poids = {1: 0, 2: 3, 3: 2, 4: 1}
    df["poids"] = df["grav"].map(poids)
    idx = df.groupby("Num_Acc")["poids"].idxmax()
    acc = df.loc[idx].copy()

    print(f"[INFO] Nombre d'accidents distincts : {acc['Num_Acc'].nunique():,}")

    if acc["com"].isna().all():
        raise RuntimeError(
            "[ERREUR] La colonne 'com' est entièrement vide : impossible de "
            "normaliser par commune. Vérifier tâches 36-38 (propagation de com)."
        )

    # -------------------------------------------------------------------
    # Agrégation par commune (com)
    # -------------------------------------------------------------------
    tableau = (
        acc.groupby("com")
        .agg(
            nb_accidents=("Num_Acc", "count"),
            nb_tues=("grav", lambda s: int((s == 2).sum())),
            nb_blesses_hospitalises=("grav", lambda s: int((s == 3).sum())),
            population=("population", "first"),
        )
        .reset_index()
    )

    tableau = tableau[tableau["population"] > 0].copy()

    tableau["taux_accidents_pour_100k"] = round(
        100_000 * tableau["nb_accidents"] / tableau["population"], 2
    )
    tableau["taux_tues_pour_100k"] = round(
        100_000 * tableau["nb_tues"] / tableau["population"], 2
    )
    tableau["taux_graves_pour_100k"] = round(
        100_000 * (tableau["nb_tues"] + tableau["nb_blesses_hospitalises"]) / tableau["population"],
        2,
    )

    tableau = tableau.sort_values("taux_accidents_pour_100k", ascending=False)

    print("\n[INFO] Taux normalisé par commune (top 10) :")
    print(tableau.head(10).to_string(index=False))

    chemin_csv = DOSSIER_RESULTATS / "taux_accidents_pour_100k.csv"
    tableau.to_csv(chemin_csv, sep=";", index=False, encoding="utf-8")
    print(f"\n[OK] Résultats sauvegardés : {chemin_csv}")

    # -------------------------------------------------------------------
    # Comparaison brut vs normalisé (pour montrer que le classement change)
    # -------------------------------------------------------------------
    tableau_brut = tableau.sort_values("nb_accidents", ascending=False)
    top_brut = set(tableau_brut.head(5)["com"])
    top_norm = set(tableau.head(5)["com"])
    if top_brut != top_norm:
        print(
            "\n[INFO] Le classement change entre nombre brut et taux normalisé : "
            f"communes en tête (brut) = {top_brut}, "
            f"communes en tête (normalisé) = {top_norm}"
        )

    # -------------------------------------------------------------------
    # Graphique
    # -------------------------------------------------------------------
    top15 = tableau.head(15)
    plt.figure(figsize=(10, 6))
    plt.barh(top15["com"].astype(str), top15["taux_accidents_pour_100k"], color="steelblue")
    plt.gca().invert_yaxis()
    plt.xlabel("Accidents pour 100 000 habitants")
    plt.ylabel("Code commune (com)")
    plt.title("Top 15 communes — Accidents normalisés par population")
    plt.tight_layout()
    chemin_png = DOSSIER_RESULTATS / "taux_accidents_pour_100k.png"
    plt.savefig(chemin_png, dpi=120)
    plt.close()
    print(f"[OK] Graphique sauvegardé : {chemin_png}")

    print("\nTÂCHE 48 TERMINÉE AVEC SUCCÈS.")


if __name__ == "__main__":
    realiser_analyse_normalisee()