"""Exécute la Tâche 38 sur la base mobilite_paris.db"""
import sqlite3
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DB_PATH = RACINE / "data" / "mobilite_paris.db"
SQL_PATH = RACINE / "src" / "tache_38_enrichissement.sql"

print(f"[INFO] Base   : {DB_PATH}")
print(f"[INFO] Script : {SQL_PATH}")

if not DB_PATH.exists():
    raise FileNotFoundError(f"Base introuvable : {DB_PATH}")
if not SQL_PATH.exists():
    raise FileNotFoundError(f"Script SQL introuvable : {SQL_PATH}")

with open(SQL_PATH, "r", encoding="utf-8") as f:
    sql_script = f.read()

conn = sqlite3.connect(DB_PATH)
try:
    conn.executescript(sql_script)
    conn.commit()
    print("[OK] Script SQL exécuté avec succès !")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT_ENRICHI")
    print(f"[OK] FAIT_ACCIDENT_ENRICHI : {cur.fetchone()[0]} lignes")

    cur.execute("PRAGMA table_info(FAIT_ACCIDENT_ENRICHI)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"[INFO] Colonnes ({len(cols)})")

    print("\n[INFO] Taux de remplissage des jointures :")
    cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT_ENRICHI")
    total = cur.fetchone()[0]
    for col in ["annee_semaine", "q_total", "meteo_precipitations", "com", "population"]:
        cur.execute(f"SELECT COUNT({col}) FROM FAIT_ACCIDENT_ENRICHI")
        n = cur.fetchone()[0]
        pct = 100 * n / total if total else 0
        print(f"  • {col:<25} : {n:>6} / {total}  ({pct:.1f}%)")

except Exception as e:
    print(f"[ERREUR] {e}")
    raise
finally:
    conn.close()