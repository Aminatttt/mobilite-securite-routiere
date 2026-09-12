"""
Tâche #31 — Rédiger le rapport de qualité (avant/après, doublons, taux de match)

Ce script compare, pour chaque source, les données RAW (avant nettoyage) et
CURATED (après nettoyage + clés de jointure, cf. tâche #30), puis mesure :

    1. AVANT / APRÈS   : nombre de lignes et de colonnes avant/après nettoyage
    2. DOUBLONS        : lignes dupliquées détectées (globalement et sur la
                          clé métier de chaque source : Num_Acc, iu_ac, ...)
    3. TAUX DE MATCH    : pour chaque paire de sources censée se joindre
                          (via Num_Acc, iu_ac, AAAAMMJJ, GEO), le % de lignes
                          d'un fichier qui trouvent une correspondance dans l'autre

Le résultat est écrit dans docs/rapport_qualite.md (Markdown), prêt à être
inclus dans le dossier final (Phase 6) ou copié dans le compte-rendu.

Comme pour construire_cles_jointure.py, le script est défensif : une source
manquante est signalée en clair dans le rapport plutôt que de faire planter
le script, pour pouvoir être relancé au fur et à mesure que le nettoyage
avance.
"""

import os
from datetime import datetime
import pandas as pd


def trouver_racine_projet(depart):
    """Même convention que nettoyer_baac_ANAS.py : remonte jusqu'au .git."""
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, ".git")):
            return dossier
        dossier = os.path.dirname(dossier)
    raise FileNotFoundError("Racine du projet introuvable (pas de .git trouvé)")


def trouver_dossier_plus_recent(chemin_source):
    """Même convention que construire_cles_jointure.py / nettoyer_baac_ANAS.py."""
    if not os.path.isdir(chemin_source):
        return None
    sous_dossiers = [d for d in os.listdir(chemin_source) if os.path.isdir(os.path.join(chemin_source, d))]
    if not sous_dossiers:
        return None
    sous_dossiers.sort(reverse=True)
    return os.path.join(chemin_source, sous_dossiers[0])


dossier_script = os.path.dirname(os.path.abspath(__file__))
racine_projet = trouver_racine_projet(dossier_script)
dossier_raw = os.path.join(racine_projet, "data", "raw")
dossier_curated = os.path.join(racine_projet, "data", "curated")
dossier_docs = os.path.join(racine_projet, "docs")
os.makedirs(dossier_docs, exist_ok=True)

# Dossier RAW BAAC le plus récent, trouvé automatiquement (même logique que
# construire_cles_jointure.py) : plus besoin de mettre à jour la date à la main.
_dossier_baac_brut = trouver_dossier_plus_recent(os.path.join(dossier_raw, "baac"))


def _chemin_raw_baac(nom_fichier):
    return os.path.join(_dossier_baac_brut, nom_fichier) if _dossier_baac_brut else None


# "raw" = chemin du RAW (auto-détecté pour BAAC, à compléter à la main pour
# les autres sources une fois leurs nettoyer_*.py écrits). "curated" pointe
# vers le fichier "_cles.csv" produit par construire_cles_jointure.py
# (tâche #30) : ce script écrit toujours en virgule, donc curated_sep reste
# "," peu importe le séparateur du RAW.
SOURCES = {
    "baac_caracteristiques": {
        "raw": _chemin_raw_baac("Caract_2024.csv"),
        "raw_sep": ";",
        "curated": os.path.join(dossier_curated, "baac", "caracteristiques_paris_2024_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "Num_Acc",
    },
    "baac_lieux": {
        "raw": _chemin_raw_baac("Lieux_2024.csv"),
        "raw_sep": ";",
        "curated": os.path.join(dossier_curated, "baac", "lieux_paris_2024_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "Num_Acc",
    },
    "baac_usagers": {
        "raw": _chemin_raw_baac("Usagers_2024.csv"),
        "raw_sep": ";",
        "curated": os.path.join(dossier_curated, "baac", "usagers_paris_2024_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "Num_Acc",
    },
    "baac_vehicules": {
        "raw": _chemin_raw_baac("Vehicules_2024.csv"),
        "raw_sep": ";",
        "curated": os.path.join(dossier_curated, "baac", "vehicules_paris_2024_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "Num_Acc",
    },
    "trafic": {
        "raw": None,
        "raw_sep": ",",
        "curated": os.path.join(dossier_curated, "trafic_nettoye_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "iu_ac",
    },
    "referentiel_geo": {
        "raw": None,
        "raw_sep": ",",
        "curated": os.path.join(dossier_curated, "referentiel_geo_nettoye_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "iu_ac",
    },
    "meteo": {
        "raw": None,
        "raw_sep": ",",
        "curated": os.path.join(dossier_curated, "meteo_nettoye_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "AAAAMMJJ",
    },
    "population": {
        "raw": None,
        "raw_sep": ";",
        "curated": os.path.join(dossier_curated, "population_paris_nettoye_cles.csv"),
        "curated_sep": ",",
        "cle_metier": "GEO",
    },
}

# Paires de sources à évaluer pour le taux de match, avec la clé de jointure
# utilisée. Adapter selon les jointures réellement faites en Phase 3.
PAIRES_JOINTURE = [
    ("baac_caracteristiques", "baac_lieux", "Num_Acc"),
    ("baac_caracteristiques", "meteo", "AAAAMMJJ"),
    ("trafic", "referentiel_geo", "iu_ac"),
    ("baac_caracteristiques", "referentiel_geo", "GEO"),
]


def lire_csv(chemin, sep=","):
    if not chemin or not os.path.exists(chemin):
        return None
    try:
        return pd.read_csv(chemin, sep=sep, low_memory=False)
    except Exception as e:
        print(f"[ERREUR] lecture {chemin} : {e}")
        return None


def stats_avant_apres(nom, raw_chemin, curated_chemin, raw_sep=",", curated_sep=","):
    df_raw = lire_csv(raw_chemin, sep=raw_sep)
    df_curated = lire_csv(curated_chemin, sep=curated_sep)

    lignes_raw = len(df_raw) if df_raw is not None else "N/A"
    cols_raw = df_raw.shape[1] if df_raw is not None else "N/A"
    lignes_cur = len(df_curated) if df_curated is not None else "N/A"
    cols_cur = df_curated.shape[1] if df_curated is not None else "N/A"

    if isinstance(lignes_raw, int) and isinstance(lignes_cur, int) and lignes_raw > 0:
        pct_conserve = f"{100 * lignes_cur / lignes_raw:.1f}%"
    else:
        pct_conserve = "N/A"

    return {
        "source": nom,
        "lignes_raw": lignes_raw,
        "colonnes_raw": cols_raw,
        "lignes_curated": lignes_cur,
        "colonnes_curated": cols_cur,
        "pct_lignes_conservees": pct_conserve,
    }, df_curated


def stats_doublons(nom, df, cle_metier):
    if df is None:
        return {"source": nom, "doublons_totaux": "N/A", "doublons_cle": "N/A"}

    doublons_totaux = int(df.duplicated().sum())
    if cle_metier and cle_metier in df.columns:
        doublons_cle = int(df.duplicated(subset=[cle_metier]).sum())
    else:
        doublons_cle = "N/A (clé absente)"

    return {
        "source": nom,
        "doublons_totaux": doublons_totaux,
        "doublons_cle": doublons_cle,
    }


def taux_de_match(nom_a, df_a, nom_b, df_b, cle):
    if df_a is None or df_b is None:
        return {
            "source_a": nom_a, "source_b": nom_b, "cle": cle,
            "taux_match_a_vers_b": "N/A (fichier manquant)",
            "taux_match_b_vers_a": "N/A (fichier manquant)",
        }
    if cle not in df_a.columns or cle not in df_b.columns:
        return {
            "source_a": nom_a, "source_b": nom_b, "cle": cle,
            "taux_match_a_vers_b": f"N/A (colonne '{cle}' absente)",
            "taux_match_b_vers_a": f"N/A (colonne '{cle}' absente)",
        }

    vals_a = df_a[cle].dropna().astype(str)
    vals_b = df_b[cle].dropna().astype(str)
    set_b = set(vals_b)
    set_a = set(vals_a)

    match_a = vals_a.isin(set_b).mean() * 100 if len(vals_a) else 0
    match_b = vals_b.isin(set_a).mean() * 100 if len(vals_b) else 0

    return {
        "source_a": nom_a, "source_b": nom_b, "cle": cle,
        "taux_match_a_vers_b": f"{match_a:.1f}%",
        "taux_match_b_vers_a": f"{match_b:.1f}%",
    }


def generer_markdown(stats_ap, stats_dup, stats_match):
    lignes = []
    lignes.append("# Rapport de qualité — ETL Phase 2\n")
    lignes.append(f"_Généré automatiquement le {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")

    lignes.append("## 1. Avant / après nettoyage\n")
    lignes.append("| Source | Lignes RAW | Colonnes RAW | Lignes CURATED | Colonnes CURATED | % lignes conservées |")
    lignes.append("|---|---|---|---|---|---|")
    for s in stats_ap:
        lignes.append(
            f"| {s['source']} | {s['lignes_raw']} | {s['colonnes_raw']} | "
            f"{s['lignes_curated']} | {s['colonnes_curated']} | {s['pct_lignes_conservees']} |"
        )

    lignes.append("\n## 2. Doublons\n")
    lignes.append("| Source | Doublons (toutes colonnes) | Doublons (clé métier) |")
    lignes.append("|---|---|---|")
    for s in stats_dup:
        lignes.append(f"| {s['source']} | {s['doublons_totaux']} | {s['doublons_cle']} |")

    lignes.append("\n## 3. Taux de match entre sources\n")
    lignes.append("| Source A | Source B | Clé | % de A trouvé dans B | % de B trouvé dans A |")
    lignes.append("|---|---|---|---|---|")
    for m in stats_match:
        lignes.append(
            f"| {m['source_a']} | {m['source_b']} | {m['cle']} | "
            f"{m['taux_match_a_vers_b']} | {m['taux_match_b_vers_a']} |"
        )

    lignes.append("\n## 4. Notes / points d'attention\n")
    lignes.append(
        "- Un taux de match bas peut venir d'un vrai non-recouvrement des données "
        "(ex : trafic non mesuré partout à Paris) ou d'un problème de clé "
        "(format de date différent, arrondi géographique trop fin/large, types "
        "non harmonisés). À vérifier au cas par cas avant d'interpréter comme "
        "une perte de qualité.\n"
        "- Les cellules 'N/A (fichier manquant)' signalent une source pas encore "
        "nettoyée / sans clés construites : relancer nettoyer_*.py puis "
        "construire_cles_jointure.py, puis ce script.\n"
    )

    return "\n".join(lignes)


def main():
    print("=== Génération du rapport de qualité (tâche #31) ===")

    stats_avant_apres_liste = []
    dfs_curated = {}
    for nom, config in SOURCES.items():
        print(f"\n--- {nom} ---")
        s, df_curated = stats_avant_apres(
            nom, config["raw"], config["curated"],
            raw_sep=config.get("raw_sep", ","), curated_sep=config.get("curated_sep", ","),
        )
        stats_avant_apres_liste.append(s)
        dfs_curated[nom] = df_curated
        print(f"   RAW={s['lignes_raw']} lignes | CURATED={s['lignes_curated']} lignes")

    stats_doublons_liste = []
    for nom, config in SOURCES.items():
        s = stats_doublons(nom, dfs_curated[nom], config["cle_metier"])
        stats_doublons_liste.append(s)
        print(f"[Doublons] {nom} : total={s['doublons_totaux']} | sur clé={s['doublons_cle']}")

    stats_match_liste = []
    for nom_a, nom_b, cle in PAIRES_JOINTURE:
        m = taux_de_match(nom_a, dfs_curated.get(nom_a), nom_b, dfs_curated.get(nom_b), cle)
        stats_match_liste.append(m)
        print(f"[Match] {nom_a} <-> {nom_b} sur {cle} : "
              f"{m['taux_match_a_vers_b']} / {m['taux_match_b_vers_a']}")

    markdown = generer_markdown(stats_avant_apres_liste, stats_doublons_liste, stats_match_liste)
    chemin_sortie = os.path.join(dossier_docs, "rapport_qualite.md")
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\n=== Rapport écrit dans : {chemin_sortie} ===")


if __name__ == "__main__":
    main()