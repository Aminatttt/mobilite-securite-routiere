"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Export de la table enrichie (Tâche 38) en CSV
===============================================================================
"""

import sqlite3
from pathlib import Path
import pandas as pd


# -----------------------------------------------------------------------------
# 1. CHEMINS
# -----------------------------------------------------------------------------
DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = (
    DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT
)
CHEMIN_DB = RACINE_PROJET / "data" / "mobilite_paris.db"
DOSSIER_SORTIE = RACINE_PROJET / "data" / "curated" / "resultats"


# -----------------------------------------------------------------------------
# 2. FONCTION D'EXPORT
# -----------------------------------------------------------------------------
def exporter_table_enrichie():
    print("=" * 80)
    print("EXPORT — FAIT_ACCIDENT_ENRICHI (Tâche 38)")
    print("=" * 80)

    if not CHEMIN_DB.exists():
        raise FileNotFoundError(f"❌ Base introuvable : {CHEMIN_DB}")

    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    print(f"📁 Dossier de sortie : {DOSSIER_SORTIE}")

    conn = sqlite3.connect(CHEMIN_DB)
    try:
        # Vérifier que la table existe
        cur = conn.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='FAIT_ACCIDENT_ENRICHI'
        """)
        if not cur.fetchone():
            raise RuntimeError(
                "❌ Table FAIT_ACCIDENT_ENRICHI introuvable. "
                "Lance d'abord 38_executer_tache.py."
            )

        # Lecture
        df = pd.read_sql("SELECT * FROM FAIT_ACCIDENT_ENRICHI", conn)

        # Export CSV
        chemin_csv = DOSSIER_SORTIE / "fait_accident_enrichi.csv"
        df.to_csv(chemin_csv, index=False, encoding="utf-8-sig")

        print(f"✅ CSV     : {chemin_csv}")
        print(f"📊 Lignes   : {len(df)}")
        print(f"📊 Colonnes : {len(df.columns)}")

    finally:
        conn.close()

    print("\n✅ EXPORT TERMINÉ.")


if __name__ == "__main__":
    exporter_table_enrichie()