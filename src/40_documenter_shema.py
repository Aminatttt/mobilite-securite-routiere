"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 40 — Documentation du schéma logique (DDL, clés, cardinalités)
===============================================================================
Ce script NE recrée PAS de base : il se connecte à la base déjà construite
(data/mobilite_paris.db, tâches 36-38) et documente son schéma :
  - DDL exact de chaque table (tel que SQLite l'a stocké)
  - clé(s) primaire(s) déclarée(s)
  - cardinalité de chaque clé de jointure (nb de lignes vs nb de valeurs
    distinctes) pour repérer si une clé est bien unique ou pas
Produit un rapport Markdown prêt à coller dans le dossier de rendu.
===============================================================================
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT
CHEMIN_DB = RACINE_PROJET / "data" / "mobilite_paris.db"
CHEMIN_RAPPORT = RACINE_PROJET / "data" / "curated" / "resultats" / "tache_40_schema_logique.md"

# Clés de jointure connues (issues des tâches 36-39) à documenter en priorité
CLES_JOINTURE = {
    "FAIT_ACCIDENT": ["Num_Acc", "GEO", "com", "iu_ac", "AAAAMMJJ"],
    "DIM_DATE": ["AAAAMMJJ"],
    "DIM_GEO": ["GEO"],
    "DIM_REFERENTIELGEO": ["iu_ac"],
    "DIM_TRAFIC": ["iu_ac", "annee_semaine"],
    "DIM_METEO": ["AAAAMMJJ"],
    "DIM_POPULATION": ["com"],
}


def documenter_schema():
    if not CHEMIN_DB.exists():
        raise FileNotFoundError(
            f"[ERREUR] Base introuvable : {CHEMIN_DB}. "
            "Lance d'abord 36_3_creer_base_sqlite.py et 37_load_curated.py."
        )

    CHEMIN_RAPPORT.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CHEMIN_DB)
    cur = conn.cursor()

    lignes_md = [
        "# Tâche 40 — Documentation du schéma logique",
        "",
        f"*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        f"Base source : `{CHEMIN_DB.name}`",
        "",
        "## 1. Liste des tables",
        "",
    ]

    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]

    for t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        lignes_md.append(f"- `{t}` : {n} lignes")
    lignes_md.append("")

    # -------------------------------------------------------------------
    # 2. DDL exact de chaque table
    # -------------------------------------------------------------------
    lignes_md.append("## 2. DDL (structure exacte des tables)")
    lignes_md.append("")
    for t in tables:
        ddl = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (t,)
        ).fetchone()[0]
        lignes_md.append(f"### `{t}`")
        lignes_md.append("```sql")
        lignes_md.append(ddl)
        lignes_md.append("```")
        lignes_md.append("")

    # -------------------------------------------------------------------
    # 3. Clés primaires déclarées
    # -------------------------------------------------------------------
    lignes_md.append("## 3. Clés primaires")
    lignes_md.append("")
    lignes_md.append("| Table | Colonne(s) clé primaire |")
    lignes_md.append("|---|---|")
    for t in tables:
        infos = cur.execute(f"PRAGMA table_info({t})").fetchall()
        pk_cols = [row[1] for row in infos if row[5] > 0]  # row[5] = pk order
        lignes_md.append(f"| `{t}` | {', '.join(pk_cols) if pk_cols else '_(aucune déclarée)_'} |")
    lignes_md.append("")

    # -------------------------------------------------------------------
    # 4. Cardinalité des clés de jointure
    # -------------------------------------------------------------------
    lignes_md.append("## 4. Cardinalité des clés de jointure")
    lignes_md.append("")
    lignes_md.append("Une clé « unique » a autant de valeurs distinctes que de lignes.")
    lignes_md.append("")
    lignes_md.append("| Table | Clé | Lignes | Valeurs distinctes | Statut |")
    lignes_md.append("|---|---|---:|---:|---|")
    for t, cols in CLES_JOINTURE.items():
        if t not in tables:
            continue
        for c in cols:
            colnames = [row[1] for row in cur.execute(f"PRAGMA table_info({t})").fetchall()]
            if c not in colnames:
                continue
            n_total = cur.execute(f"SELECT COUNT({c}) FROM {t}").fetchone()[0]
            n_distinct = cur.execute(f"SELECT COUNT(DISTINCT {c}) FROM {t}").fetchone()[0]
            statut = "✅ unique" if n_total == n_distinct else "⚠️ dupliquée"
            lignes_md.append(f"| `{t}` | `{c}` | {n_total} | {n_distinct} | {statut} |")
    lignes_md.append("")

    lignes_md.append("---")
    lignes_md.append("*Rapport généré automatiquement par `40_documenter_schema_logique.py`.*")

    CHEMIN_RAPPORT.write_text("\n".join(lignes_md), encoding="utf-8")
    conn.close()
    print(f"[OK] Rapport Markdown généré : {CHEMIN_RAPPORT}")


if __name__ == "__main__":
    documenter_schema()