"""
===============================================================================
PROJET : Mobilité et Sécurité Routière à Paris
MODULE : Tâche 39 — Contrôle du taux de match et des doublons de jointure
===============================================================================
Contrôle qualité de FAIT_ACCIDENT_ENRICHI (produite par la tâche 38) :
  1. Contrôle du grain : FAIT_ACCIDENT_ENRICHI ne doit pas dupliquer les
     accidents/usagers de FAIT_ACCIDENT (un id_fait = une ligne).
  2. Contrôle de cardinalité : chaque dimension jointe (DIM_TRAFIC,
     DIM_METEO, DIM_POPULATION, DIM_DATE) doit avoir une clé de jointure
     unique, sans quoi la jointure duplique des lignes.
  3. Taux de remplissage (match) de chaque colonne issue d'une jointure.
  4. Limites connues, documentées automatiquement selon les résultats.

Génère un rapport Markdown dans data/curated/resultats/ et l'affiche aussi
à l'écran. Ne modifie aucune donnée : lecture seule.
===============================================================================
"""

import sqlite3
from pathlib import Path
from datetime import datetime

RACINE = Path(__file__).resolve().parent.parent
DB_PATH = RACINE / "data" / "mobilite_paris.db"
RAPPORT_PATH = RACINE / "data" / "curated" / "resultats" / "tache_39_controle_qualite.md"


def executer():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    lignes_rapport = []

    def ajouter(txt=""):
        print(txt)
        lignes_rapport.append(txt)

    ajouter("# Tâche 39 — Contrôle du taux de match et des doublons de jointure")
    ajouter("")
    ajouter(f"*Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    ajouter("")

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='FAIT_ACCIDENT_ENRICHI'"
    )
    if not cur.fetchone():
        raise RuntimeError(
            "❌ FAIT_ACCIDENT_ENRICHI introuvable. Lancer d'abord 38_executer_tache.py."
        )

    # -------------------------------------------------------------------
    # 1. CONTRÔLE DU GRAIN (doublons de jointure)
    # -------------------------------------------------------------------
    ajouter("## 1. Contrôle du grain (doublons de jointure)")
    ajouter("")
    n_fait = cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT").fetchone()[0]
    n_enrichi = cur.execute("SELECT COUNT(*) FROM FAIT_ACCIDENT_ENRICHI").fetchone()[0]
    n_distinct_id = cur.execute(
        "SELECT COUNT(DISTINCT id_fait) FROM FAIT_ACCIDENT_ENRICHI"
    ).fetchone()[0]

    grain_ok = (n_enrichi == n_fait == n_distinct_id)
    statut_grain = "✅ OK — aucun doublon introduit par les jointures" if grain_ok else "❌ ANOMALIE — doublons détectés"

    ajouter(f"- Lignes dans `FAIT_ACCIDENT` (grain de référence, usager × accident) : **{n_fait}**")
    ajouter(f"- Lignes dans `FAIT_ACCIDENT_ENRICHI` : **{n_enrichi}**")
    ajouter(f"- `id_fait` distincts dans `FAIT_ACCIDENT_ENRICHI` : **{n_distinct_id}**")
    ajouter(f"- **Statut : {statut_grain}**")

    if not grain_ok:
        cur.execute("""
            SELECT id_fait, COUNT(*) AS n
            FROM FAIT_ACCIDENT_ENRICHI
            GROUP BY id_fait
            HAVING COUNT(*) > 1
            ORDER BY n DESC
            LIMIT 5
        """)
        doublons = cur.fetchall()
        ajouter(f"  - Exemples d'`id_fait` dupliqués (top 5) : `{doublons}`")
        ajouter(
            "  - ⚠️ À investiguer : une dimension jointe a probablement plusieurs lignes "
            "pour une même clé de jointure (voir section 2)."
        )
    ajouter("")

    # -------------------------------------------------------------------
    # 2. CARDINALITÉ DES CLÉS DE JOINTURE
    # -------------------------------------------------------------------
    ajouter("## 2. Cardinalité des clés de jointure")
    ajouter("")
    ajouter("Une clé dupliquée dans une dimension multiplie mécaniquement les lignes "
            "de `FAIT_ACCIDENT_ENRICHI` lors du `LEFT JOIN`.")
    ajouter("")
    ajouter("| Dimension | Clé de jointure | Lignes | Clés dupliquées | Statut |")
    ajouter("|---|---|---:|---:|---|")

    controles_cardinalite = [
        ("DIM_DATE", ["AAAAMMJJ"]),
        ("DIM_TRAFIC", ["iu_ac", "annee_semaine"]),
        ("DIM_METEO", ["AAAAMMJJ"]),
        ("DIM_POPULATION", ["com"]),
    ]
    for table, cles in controles_cardinalite:
        try:
            cle_sql = ", ".join(cles)
            total = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            n_dupliquees = cur.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT {cle_sql} FROM {table} GROUP BY {cle_sql} HAVING COUNT(*) > 1
                )
            """).fetchone()[0]
            statut = "✅ unique" if n_dupliquees == 0 else "⚠️ dupliquée"
            ajouter(f"| `{table}` | `{cle_sql}` | {total} | {n_dupliquees} | {statut} |")
        except Exception as e:
            ajouter(f"| `{table}` | `{', '.join(cles)}` | — | — | contrôle impossible ({e}) |")
    ajouter("")

    # -------------------------------------------------------------------
    # 3. TAUX DE REMPLISSAGE (MATCH) DES JOINTURES
    # -------------------------------------------------------------------
    ajouter("## 3. Taux de remplissage (match) des jointures")
    ajouter("")
    ajouter("| Colonne | Renseignées | Total | Taux |")
    ajouter("|---|---:|---:|---:|")

    total_enrichi = n_enrichi
    colonnes_a_verifier = [
        "annee_semaine", "q_total", "q_moyen", "k_moyen",
        "meteo_precipitations", "meteo_temp_min", "meteo_temp_max", "meteo_temp_moy",
        "com", "population", "population_annee",
    ]
    taux = {}
    for col in colonnes_a_verifier:
        try:
            n = cur.execute(f"SELECT COUNT({col}) FROM FAIT_ACCIDENT_ENRICHI").fetchone()[0]
            pct = 100 * n / total_enrichi if total_enrichi else 0
            taux[col] = pct
            ajouter(f"| `{col}` | {n} | {total_enrichi} | {pct:.1f}% |")
        except Exception:
            ajouter(f"| `{col}` | — | {total_enrichi} | colonne absente |")
    ajouter("")

    # -------------------------------------------------------------------
    # 4. LIMITES CONNUES (générées selon les résultats observés)
    # -------------------------------------------------------------------
    ajouter("## 4. Limites connues")
    ajouter("")
    q_total_pct = taux.get("q_total")
    if q_total_pct is not None and q_total_pct < 90:
        ajouter(
            f"- **`q_total` / `q_moyen` / `k_moyen` ({q_total_pct:.1f}%)** : `iu_ac` (capteur "
            f"trafic le plus proche) est identifié pour la grande majorité des accidents dans "
            f"`FAIT_ACCIDENT` (matching exact sur `GEO` puis par proximité ~1 km), mais un "
            f"capteur identifié n'a pas systématiquement de mesure trafic pour la semaine "
            f"exacte de l'accident. C'est une limite de couverture temporelle du réseau de "
            f"capteurs, pas un défaut de la jointure elle-même."
        )
    ajouter(
        "- `population` est calculée sur la mesure INSEE **« Population totale »** "
        "(= population municipale + population comptée à part), sur la période la plus "
        "récente disponible dans la source ; les autres mesures/périodes sont écartées."
    )
    ajouter(
        "- `DIM_TRAFIC` est agrégée au **grain hebdomadaire** (moyenne des mesures "
        "quotidiennes de la semaine par capteur) : `q_total`/`q_moyen`/`k_moyen` dans "
        "`FAIT_ACCIDENT_ENRICHI` représentent une moyenne hebdomadaire du trafic, pas une "
        "mesure instantanée du jour précis de l'accident."
    )
    ajouter("")
    ajouter("---")
    ajouter(f"*Rapport généré automatiquement par `39_controle_qualite.py` — "
            f"base : `{DB_PATH.name}`.*")

    conn.close()

    RAPPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAPPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes_rapport) + "\n")

    print(f"\n[OK] Rapport Markdown généré : {RAPPORT_PATH}")


if __name__ == "__main__":
    executer()