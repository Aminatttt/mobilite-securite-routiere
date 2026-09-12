"""


Fichiers attendus :
- Q_75_previous-1950-2024_RR-T-Vent.csv
- Q_75_previous-1950-2024_autres-parametres.csv

Pipeline :
    RAW
      ↓
    Lecture CSV / gzip
      ↓
    Conversion des dates
      ↓
    Filtre 2020-2024
      ↓
    Contrôles qualité
      ↓
    Nettoyage
      ↓
    CURATED

Le RAW n'est jamais modifié.

Sorties :
- meteo_rrtvent_paris_clean.csv
- meteo_autres_paris_clean.csv
- meteo_paris_reference_daily.csv
- meteo_stations_completude.csv
- rapport_qualite_meteo.csv
"""

import logging
from pathlib import Path

import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

RAW_METEO_ROOTS = [
    BASE_DIR / "data" / "raw" / "meteo",
    SCRIPT_DIR / "data" / "raw" / "meteo",
]

RAW_METEO_ROOT = next(
    (root for root in RAW_METEO_ROOTS if root.exists() and any(d.is_dir() for d in root.iterdir())),
    RAW_METEO_ROOTS[0],
)

CURATED_DIR = BASE_DIR / "data" / "curated" / "meteo"

CURATED_DIR.mkdir(parents=True, exist_ok=True)

DATE_DEBUT = pd.Timestamp("2020-01-01")
DATE_FIN = pd.Timestamp("2024-12-31")

SEPARATEUR = ";"

SEUIL_COLONNE_VIDE = 99.0

COL_STATION = "NUM_POSTE"
COL_DATE_BRUTE = "AAAAMMJJ"
COL_DATE = "date"


# ============================================================
# 2. LOGS
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("nettoyer_meteo")


# ============================================================
# 3. LOCALISATION DES FICHIERS
# ============================================================

def dernier_dossier_meteo():
    """
    Cherche le dernier dossier présent dans l'un des chemins RAW météo connus.
    Les dossiers sont généralement organisés par date.
    """

    racines = [
        BASE_DIR / "data" / "raw" / "meteo",
        SCRIPT_DIR / "data" / "raw" / "meteo",
    ]

    racine = next(
        (
            root for root in racines
            if root.exists() and any(d.is_dir() for d in root.iterdir())
        ),
        None,
    )

    if racine is None:
        raise FileNotFoundError(
            f"Aucun sous-dossier trouvé dans : {racines[0]} ou {racines[1]}"
        )

    dossiers = sorted(
        (d for d in racine.iterdir() if d.is_dir()),
        key=lambda x: x.name,
    )

    if not dossiers:
        raise FileNotFoundError(
            f"Aucun sous-dossier trouvé dans : {racine}"
        )

    dossier = dossiers[-1]

    logger.info(f"Dossier météo utilisé : {dossier}")

    return dossier


def localiser_fichiers():
    """
    Recherche les deux fichiers météo.
    """

    dossier = dernier_dossier_meteo()

    fichiers = {}

    for chemin in dossier.glob("*.csv"):

        nom = chemin.name.lower()

        if "rr-t-vent" in nom or "rr_t_vent" in nom:
            fichiers["rrtvent"] = chemin

        elif (
            "autres-parametres" in nom
            or "autres_parametres" in nom
        ):
            fichiers["autres"] = chemin

    if "rrtvent" not in fichiers:
        raise FileNotFoundError(
            "Fichier RR-T-Vent introuvable."
        )

    if "autres" not in fichiers:
        logger.warning(
            "Fichier autres-parametres introuvable. "
            "Le traitement continuera avec RR-T-Vent."
        )

    for type_fichier, chemin in fichiers.items():
        logger.info(
            f"Fichier {type_fichier} : {chemin.name}"
        )

    return fichiers


# ============================================================
# 4. DETECTION GZIP
# ============================================================

def est_gzip(chemin):
    """
    Détecte si le fichier est réellement compressé en gzip,
    même si son extension est .csv.
    """

    with open(chemin, "rb") as fichier:
        entete = fichier.read(2)

    return entete == b"\x1f\x8b"


# ============================================================
# 5. LECTURE DES CSV
# ============================================================

def lire_csv_meteo(chemin):
    """
    Lit un fichier météo CSV ou CSV compressé en gzip.
    """

    compression = "gzip" if est_gzip(chemin) else None

    if compression == "gzip":
        logger.info(
            f"Compression gzip détectée : {chemin.name}"
        )

    df = pd.read_csv(
        chemin,
        sep=SEPARATEUR,
        compression=compression,
        low_memory=False,
    )

    logger.info(
        f"Lecture terminée : "
        f"{len(df):,} lignes / {len(df.columns)} colonnes"
    )

    return df


# ============================================================
# 6. CONVERSION DE LA DATE
# ============================================================

def convertir_date(df):
    """
    Transforme AAAAMMJJ en véritable date pandas.
    """

    if COL_DATE_BRUTE not in df.columns:
        raise KeyError(
            f"Colonne obligatoire absente : {COL_DATE_BRUTE}"
        )

    df[COL_DATE] = pd.to_datetime(
        df[COL_DATE_BRUTE].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    nb_invalides = df[COL_DATE].isna().sum()

    if nb_invalides > 0:
        logger.warning(
            f"Dates invalides détectées : {nb_invalides:,}"
        )

    return df, nb_invalides


# ============================================================
# 7. FILTRE 2020-2024
# ============================================================

def filtrer_periode(df):
    """
    Conserve uniquement la période 2020-2024.
    """

    avant = len(df)

    df = df[
        (df[COL_DATE] >= DATE_DEBUT)
        & (df[COL_DATE] <= DATE_FIN)
    ].copy()

    apres = len(df)

    logger.info(
        f"Filtre période 2020-2024 : "
        f"{avant:,} -> {apres:,} lignes"
    )

    return df, avant - apres


# ============================================================
# 8. COLONNES QUASI VIDES
# ============================================================

def supprimer_colonnes_vides(df, nom_fichier):
    """
    Supprime uniquement les colonnes dont plus de 99 %
    des valeurs sont manquantes.
    """

    pourcentage_manquant = df.isna().mean() * 100

    colonnes_supprimees = (
        pourcentage_manquant[
            pourcentage_manquant > SEUIL_COLONNE_VIDE
        ]
        .index
        .tolist()
    )

    if colonnes_supprimees:

        logger.info(
            f"[{nom_fichier}] "
            f"{len(colonnes_supprimees)} colonnes "
            f"quasi vides supprimées."
        )

        df = df.drop(
            columns=colonnes_supprimees
        )

    return df, colonnes_supprimees


# ============================================================
# 9. COLONNES DE QUALITE Q*
# ============================================================

def typer_colonnes_qualite(df):
    """
    Convertit les colonnes Q* en nombres entiers nullable.

    Exemple :
        RR  -> mesure de pluie
        QRR -> code qualité de RR

    On ne supprime PAS les Q* automatiquement.
    """

    colonnes_qualite = [
        colonne
        for colonne in df.columns
        if colonne.startswith("Q")
        and colonne != COL_DATE
    ]

    for colonne in colonnes_qualite:

        df[colonne] = pd.to_numeric(
            df[colonne],
            errors="coerce",
        ).astype("Int8")

    logger.info(
        f"Colonnes qualité détectées : "
        f"{len(colonnes_qualite)}"
    )

    return df, colonnes_qualite


# ============================================================
# 10. DOUBLONS
# ============================================================

def analyser_doublons(df):
    """
    Compte les doublons sur (station, date).
    """

    if (
        COL_STATION not in df.columns
        or COL_DATE not in df.columns
    ):
        return 0

    doublons = df.duplicated(
        subset=[COL_STATION, COL_DATE],
        keep="first",
    ).sum()

    return int(doublons)


def supprimer_doublons(df, nom_fichier):
    """
    Supprime les doublons station + date.
    """

    if (
        COL_STATION not in df.columns
        or COL_DATE not in df.columns
    ):
        logger.warning(
            f"[{nom_fichier}] "
            "Impossible de contrôler les doublons "
            "(clé station/date absente)."
        )
        return df, 0

    doublons = analyser_doublons(df)

    df = df.drop_duplicates(
        subset=[COL_STATION, COL_DATE],
        keep="first",
    ).copy()

    logger.info(
        f"[{nom_fichier}] "
        f"Doublons supprimés : {doublons:,}"
    )

    return df, doublons


# ============================================================
# 11. NETTOYAGE COMPLET D'UN FICHIER
# ============================================================

def nettoyer_fichier(chemin, nom_fichier):

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"NETTOYAGE : {nom_fichier}")
    logger.info("=" * 60)

    # Lecture
    df = lire_csv_meteo(chemin)

    lignes_initiales = len(df)
    colonnes_initiales = len(df.columns)

    # Date
    df, dates_invalides = convertir_date(df)

    # Filtre 2020-2024
    df, lignes_hors_periode = filtrer_periode(df)

    # Colonnes quasi vides
    df, colonnes_supprimees = supprimer_colonnes_vides(
        df,
        nom_fichier,
    )

    # Colonnes Q*
    df, colonnes_qualite = typer_colonnes_qualite(df)

    # Doublons
    df, doublons = supprimer_doublons(
        df,
        nom_fichier,
    )

    lignes_finales = len(df)
    colonnes_finales = len(df.columns)

    logger.info(
        f"Lignes finales : "
        f"{lignes_initiales:,} -> {lignes_finales:,}"
    )

    logger.info(
        f"Colonnes finales : "
        f"{colonnes_initiales} -> {colonnes_finales}"
    )

    rapport = {
        "fichier": nom_fichier,
        "lignes_avant": lignes_initiales,
        "lignes_apres": lignes_finales,
        "colonnes_avant": colonnes_initiales,
        "colonnes_apres": colonnes_finales,
        "dates_invalides": dates_invalides,
        "lignes_hors_periode": lignes_hors_periode,
        "doublons_supprimes": doublons,
        "nb_colonnes_qualite": len(colonnes_qualite),
        "nb_colonnes_supprimees": len(colonnes_supprimees),
    }

    return df, rapport


# ============================================================
# 12. STATION DE REFERENCE
# ============================================================

def detecter_station_reference(df):
    """
    Détermine la station ayant la meilleure couverture
    sur la période 2020-2024.

    ATTENTION :
    Cette fonction donne une proposition automatique.
    Le choix final de la station doit être documenté.
    """

    if COL_STATION not in df.columns:
        raise KeyError(
            f"Colonne {COL_STATION} absente."
        )

    variables_essentielles = [
        colonne
        for colonne in ["RR", "TN", "TX"]
        if colonne in df.columns
    ]

    agregations = {
        "nb_jours": (COL_DATE, "count"),
        "date_min": (COL_DATE, "min"),
        "date_max": (COL_DATE, "max"),
    }

    for variable in variables_essentielles:
        agregations[
            f"pct_manquant_{variable}"
        ] = (
            variable,
            lambda s: s.isna().mean() * 100
        )

    stats = (
        df
        .groupby(COL_STATION)
        .agg(**agregations)
    )

    stats["duree_couverture_jours"] = (
        stats["date_max"]
        - stats["date_min"]
    ).dt.days + 1

    stats["taux_completude"] = (
        stats["nb_jours"]
        / stats["duree_couverture_jours"]
    )

    stats = stats.sort_values(
        by=[
            "taux_completude",
            "nb_jours",
        ],
        ascending=False,
    )

    station_reference = stats.index[0]

    logger.info("")
    logger.info(
        f"Station de référence proposée : "
        f"{station_reference}"
    )

    logger.info(
        f"Couverture : "
        f"{stats.loc[station_reference, 'date_min'].date()} "
        f"-> "
        f"{stats.loc[station_reference, 'date_max'].date()}"
    )

    logger.info(
        f"Taux de complétude : "
        f"{stats.loc[station_reference, 'taux_completude'] * 100:.2f}%"
    )

    return station_reference, stats


# ============================================================
# 13. FUSION DES DEUX FICHIERS
# ============================================================

def fusionner_station_reference(
    df_rrtvent,
    df_autres,
    station_reference,
):
    """
    Fusionne les deux fichiers météo sur :

        NUM_POSTE + date

    uniquement pour la station de référence.
    """

    df_rr = df_rrtvent[
        df_rrtvent[COL_STATION] == station_reference
    ].copy()

    df_autres_ref = df_autres[
        df_autres[COL_STATION] == station_reference
    ].copy()

    lignes_avant = len(df_rr)

    # Colonnes qui ne doivent pas être dupliquées
    colonnes_communes = [
        COL_STATION,
        COL_DATE,
        "NOM_USUEL",
        "LAT",
        "LON",
        "ALTI",
        COL_DATE_BRUTE,
    ]

    colonnes_a_supprimer = [
        colonne
        for colonne in colonnes_communes
        if colonne in df_autres_ref.columns
        and colonne != COL_STATION
        and colonne != COL_DATE
    ]

    df_autres_ref = df_autres_ref.drop(
        columns=colonnes_a_supprimer,
        errors="ignore",
    )

    # Vérification de l'unicité
    doublons_autres = df_autres_ref.duplicated(
        subset=[COL_STATION, COL_DATE]
    ).sum()

    if doublons_autres > 0:

        logger.warning(
            f"Doublons détectés dans autres-parametres "
            f"avant fusion : {doublons_autres}"
        )

        df_autres_ref = df_autres_ref.drop_duplicates(
            subset=[COL_STATION, COL_DATE],
            keep="first",
        )

    # Merge
    df_merge = df_rr.merge(
        df_autres_ref,
        on=[COL_STATION, COL_DATE],
        how="left",
        suffixes=("", "_autres"),
        indicator=True,
    )

    lignes_apres = len(df_merge)

    lignes_matchees = (
        df_merge["_merge"] == "both"
    ).sum()

    taux_match = (
        lignes_matchees / lignes_avant * 100
        if lignes_avant > 0
        else 0
    )

    df_merge = df_merge.drop(
        columns=["_merge"]
    )

    logger.info("")
    logger.info("FUSION METEO")
    logger.info(
        f"Lignes avant fusion : {lignes_avant:,}"
    )
    logger.info(
        f"Lignes après fusion : {lignes_apres:,}"
    )
    logger.info(
        f"Lignes matchées : {lignes_matchees:,}"
    )
    logger.info(
        f"Taux de match : {taux_match:.2f}%"
    )

    rapport_fusion = {
        "station_reference": station_reference,
        "lignes_avant_fusion": lignes_avant,
        "lignes_apres_fusion": lignes_apres,
        "lignes_matchees": int(lignes_matchees),
        "taux_match_pourcent": round(
            taux_match,
            2,
        ),
    }

    return df_merge, rapport_fusion


# ============================================================
# 14. PROGRAMME PRINCIPAL
# ============================================================

def main():

    logger.info("")
    logger.info("=" * 70)
    logger.info(
        "NETTOYAGE DES DONNEES METEO - PARIS (DEP 75)"
    )
    logger.info("=" * 70)

    # --------------------------------------------------------
    # Localisation
    # --------------------------------------------------------

    fichiers = localiser_fichiers()

    rapport_global = []

    # --------------------------------------------------------
    # RR-T-Vent
    # --------------------------------------------------------

    df_rrtvent, rapport_rr = nettoyer_fichier(
        fichiers["rrtvent"],
        "RR-T-Vent",
    )

    rapport_global.append(rapport_rr)

    chemin_rrtvent = (
        CURATED_DIR
        / "meteo_rrtvent_paris_clean.csv"
    )

    df_rrtvent.to_csv(
        chemin_rrtvent,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    logger.info(
        f"Fichier CURATED sauvegardé : "
        f"{chemin_rrtvent}"
    )

    # --------------------------------------------------------
    # Autres paramètres
    # --------------------------------------------------------

    df_autres = None

    if "autres" in fichiers:

        df_autres, rapport_autres = nettoyer_fichier(
            fichiers["autres"],
            "autres-parametres",
        )

        rapport_global.append(
            rapport_autres
        )

        chemin_autres = (
            CURATED_DIR
            / "meteo_autres_paris_clean.csv"
        )

        df_autres.to_csv(
            chemin_autres,
            index=False,
            encoding="utf-8-sig",
            sep=";",
        )

        logger.info(
            f"Fichier CURATED sauvegardé : "
            f"{chemin_autres}"
        )

    # --------------------------------------------------------
    # Station de référence
    # --------------------------------------------------------

    station_reference, stats_stations = (
        detecter_station_reference(
            df_rrtvent
        )
    )

    chemin_stats = (
        CURATED_DIR
        / "meteo_stations_completude.csv"
    )

    stats_stations.reset_index().to_csv(
        chemin_stats,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    logger.info(
        f"Statistiques stations sauvegardées : "
        f"{chemin_stats}"
    )

    # --------------------------------------------------------
    # Fusion des deux sources météo
    # --------------------------------------------------------

    rapport_fusion = None

    if df_autres is not None:

        df_reference, rapport_fusion = (
            fusionner_station_reference(
                df_rrtvent,
                df_autres,
                station_reference,
            )
        )

    else:

        df_reference = df_rrtvent[
            df_rrtvent[COL_STATION]
            == station_reference
        ].copy()

    chemin_reference = (
        CURATED_DIR
        / "meteo_paris_reference_daily.csv"
    )

    df_reference.to_csv(
        chemin_reference,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    logger.info(
        f"Série météo de référence sauvegardée : "
        f"{chemin_reference}"
    )

    # --------------------------------------------------------
    # Rapport qualité
    # --------------------------------------------------------

    rapport_df = pd.DataFrame(
        rapport_global
    )

    chemin_rapport = (
        CURATED_DIR
        / "rapport_qualite_meteo.csv"
    )

    rapport_df.to_csv(
        chemin_rapport,
        index=False,
        encoding="utf-8-sig",
        sep=";",
    )

    logger.info(
        f"Rapport qualité sauvegardé : "
        f"{chemin_rapport}"
    )

    # --------------------------------------------------------
    # Rapport fusion
    # --------------------------------------------------------

    if rapport_fusion is not None:

        chemin_rapport_fusion = (
            CURATED_DIR
            / "rapport_fusion_meteo.csv"
        )

        pd.DataFrame(
            [rapport_fusion]
        ).to_csv(
            chemin_rapport_fusion,
            index=False,
            encoding="utf-8-sig",
            sep=";",
        )

        logger.info(
            f"Rapport fusion sauvegardé : "
            f"{chemin_rapport_fusion}"
        )

    # --------------------------------------------------------
    # Fin
    # --------------------------------------------------------

    logger.info("")
    logger.info("=" * 70)
    logger.info("NETTOYAGE METEO TERMINE")
    logger.info("=" * 70)


# ============================================================
# 15. EXECUTION
# ============================================================

if __name__ == "__main__":
    main()