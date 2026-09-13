"""
ANALYSE TEMPORELLE (TACHE 44) — Phase 4 : Analyse exploratoire
---------------------------------------------------------------

Question métier :
    "Analyse par heure, jour de semaine, mois/saison et jours fériés."

OBJECTIF
--------
Analyser quand les accidents corporels se produisent à Paris :

    - par heure
    - par jour de la semaine
    - par mois
    - par saison
    - les jours fériés vs jours ordinaires

SOURCES
-------
1. data/mobilite_paris.db
   Table : FAIT_ACCIDENT_ENRICHI

   Utilisée pour :
       - Num_Acc
       - AAAAMMJJ
       - annee
       - mois
       - grav
       - informations temporelles

2. data/curated/caracteristiques_paris_clean.csv

   Utilisée pour récupérer :
       - Num_Acc
       - jour
       - mois
       - an
       - hrmn

   IMPORTANT :
   Dans le fichier BAAC actuel, la date n'est pas encore une
   colonne "date". Elle est reconstruite à partir de :
       an + mois + jour

GRAIN
-----
Le fichier FAIT_ACCIDENT_ENRICHI est au grain USAGER.

Pour analyser le nombre d'ACCIDENTS, on transforme les données
au grain :

    1 ligne = 1 accident

Un accident est considéré comme grave si au moins un usager
de cet accident possède :

    grav = 2  -> Tué
    grav = 3  -> Blessé hospitalisé

SORTIES
-------
dashboard/
    temporel_heure.png
    temporel_jour_semaine.png
    temporel_mois_saison.png
    temporel_jours_feries.png

data/curated/
    accidents_analyse_temporelle.csv
    temporel_accidents_par_heure.csv
    temporel_accidents_par_jour.csv
    temporel_accidents_par_mois.csv
    temporel_accidents_par_saison.csv
    temporel_accidents_jours_feries.csv

DEPENDANCE
----------
Installer si nécessaire :

    pip install holidays
"""

from pathlib import Path
import sqlite3

import pandas as pd
import matplotlib.pyplot as plt

try:
    import holidays
except ImportError:
    holidays = None


# ============================================================
# 0. RACINE DU PROJET
# ============================================================

def trouver_racine_projet(depart: Path) -> Path:
    """
    Recherche la vraie racine du projet.

    Le dossier src contient aussi un sous-dossier data, mais ce n'est pas
    la racine du projet. On cherche donc l'ancêtre qui contient à la fois :
        - un dossier 'src'
        - un dossier 'data'
        - idéalement un README.md ou un dossier 'dashboard'
    """

    curr = depart.resolve()

    while curr != curr.parent:

        if (
            (curr / "src").is_dir()
            and (curr / "data").is_dir()
            and (
                (curr / "README.md").exists()
                or (curr / "dashboard").is_dir()
            )
        ):
            return curr

        curr = curr.parent

    return depart.resolve()


RACINE_PROJET = trouver_racine_projet(Path.cwd())


# ============================================================
# 1. CHEMINS
# ============================================================

DB_PATH = (
    RACINE_PROJET
    / "data"
    / "mobilite_paris.db"
)

USAGERS_PATH = (
    RACINE_PROJET / "data" / "curated" / "baac" / "usagers_paris_2024_cles.csv"
)

CARACT_PATH = (
    RACINE_PROJET / "data" / "curated" / "baac" / "caracteristiques_paris_2024_cles.csv"
)

DOSSIER_DASHBOARD = (
    RACINE_PROJET
    / "dashboard"
)

DOSSIER_CURATED = (
    RACINE_PROJET
    / "data"
    / "curated"
)

DOSSIER_DASHBOARD.mkdir(
    parents=True,
    exist_ok=True
)

DOSSIER_CURATED.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. VERIFICATION DES FICHIERS
# ============================================================

print("=" * 70)
print("ANALYSE TEMPORELLE — TACHE 44")
print("=" * 70)

print("\n[INFO] Racine du projet :")
print(RACINE_PROJET)

print("\n[INFO] Base SQLite :")
print(DB_PATH)

print("\n[INFO] Fichier caractéristiques :")
print(CARACT_PATH)


def construire_db_fallback() -> None:
    """
    Construit automatiquement la base SQLite attendue à partir des
    fichiers CSV nettoyés du projet lorsque la base est absente ou
    incomplète.
    """

    if not CARACT_PATH.exists():
        raise FileNotFoundError(
            f"Fichier BAAC introuvable : {CARACT_PATH}"
        )

    if not USAGERS_PATH.exists():
        raise FileNotFoundError(
            f"Fichier usagers introuvable : {USAGERS_PATH}"
        )

    print("\n[WARN] Base SQLite absente ou incomplète. Génération automatique à partir des CSV nettoyés...")

    caract = pd.read_csv(
        CARACT_PATH,
        sep=";",
        encoding="utf-8-sig",
        usecols=["Num_Acc", "jour", "mois", "an"],
        low_memory=False
    )

    usagers = pd.read_csv(
        USAGERS_PATH,
        sep=";",
        encoding="utf-8-sig",
        usecols=["Num_Acc", "grav"],
        low_memory=False
    )

    for df in (caract, usagers):
        df["Num_Acc"] = df["Num_Acc"].astype("string").str.strip()

    caract["an"] = pd.to_numeric(caract["an"], errors="coerce")
    caract["mois"] = pd.to_numeric(caract["mois"], errors="coerce")
    caract["jour"] = pd.to_numeric(caract["jour"], errors="coerce")

    caract["date_complete"] = pd.to_datetime(
        caract["an"].astype("Int64").astype("string")
        + "-"
        + caract["mois"].astype("Int64").astype("string").str.zfill(2)
        + "-"
        + caract["jour"].astype("Int64").astype("string").str.zfill(2),
        errors="coerce"
    )

    caract["AAAAMMJJ"] = (
        caract["date_complete"].dt.strftime("%Y%m%d")
    )

    caract = (
        caract[["Num_Acc", "AAAAMMJJ", "an", "mois"]]
        .rename(columns={"an": "annee"})
        .drop_duplicates(subset="Num_Acc")
    )

    usagers["grav"] = pd.to_numeric(usagers["grav"], errors="coerce")

    df_fait = usagers.merge(
        caract,
        on="Num_Acc",
        how="inner"
    )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS FAIT_ACCIDENT_ENRICHI")
        df_fait.to_sql(
            "FAIT_ACCIDENT_ENRICHI",
            conn,
            index=False,
            if_exists="replace"
        )

    print(f"[OK] Base SQLite reconstruite : {DB_PATH}")


if not DB_PATH.exists():
    construire_db_fallback()
else:
    with sqlite3.connect(DB_PATH) as conn:
        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='FAIT_ACCIDENT_ENRICHI'",
            conn
        )
        if tables.empty:
            construire_db_fallback()
        else:
            colonnes = pd.read_sql(
                "PRAGMA table_info(FAIT_ACCIDENT_ENRICHI)",
                conn
            )
            colonnes_requises = {"Num_Acc", "AAAAMMJJ", "annee", "mois", "grav"}
            if not colonnes_requises.issubset(set(colonnes["name"])):
                construire_db_fallback()


if not CARACT_PATH.exists():

    raise FileNotFoundError(
        f"Fichier BAAC introuvable : {CARACT_PATH}"
    )


# ============================================================
# 3. CHARGEMENT DE FAIT_ACCIDENT_ENRICHI
# ============================================================

print("\n[1/7] Chargement de FAIT_ACCIDENT_ENRICHI...")


conn = sqlite3.connect(DB_PATH)

df_fait = pd.read_sql(
    """
    SELECT
        Num_Acc,
        AAAAMMJJ,
        annee,
        mois,
        grav
    FROM FAIT_ACCIDENT_ENRICHI
    """,
    conn
)

conn.close()


print(
    f"[INFO] Lignes usagers chargées : "
    f"{len(df_fait):,}"
)


# ============================================================
# 4. NORMALISATION DES TYPES
# ============================================================

df_fait["Num_Acc"] = (
    df_fait["Num_Acc"]
    .astype("string")
    .str.strip()
)


df_fait["AAAAMMJJ"] = (
    df_fait["AAAAMMJJ"]
    .astype("string")
    .str.strip()
)


df_fait["grav"] = pd.to_numeric(
    df_fait["grav"],
    errors="coerce"
)


# ============================================================
# 5. CONSTRUCTION DU GRAIN ACCIDENT
# ============================================================

print("\n[2/7] Passage du grain usager au grain accident...")


# Un accident est grave si AU MOINS UN de ses usagers
# possède grav = 2 ou grav = 3.

df_fait["est_grave_usager"] = (
    df_fait["grav"].isin([2, 3])
)


# Agrégation par accident.
#
# any() signifie :
#
#     Est-ce qu'au moins un usager est grave ?
#
# Exemple :
#
# Num_Acc     grav
# A           1
# A           4
# A           3
#
# devient :
#
# Num_Acc     est_grave
# A           True

df_acc = (
    df_fait
    .groupby("Num_Acc", as_index=False)
    .agg(
        AAAAMMJJ=("AAAAMMJJ", "first"),
        annee=("annee", "first"),
        mois=("mois", "first"),
        est_grave=("est_grave_usager", "any")
    )
)


print(
    f"[INFO] Accidents uniques : "
    f"{len(df_acc):,}"
)


# ============================================================
# 6. CHARGEMENT DES CARACTERISTIQUES BAAC
# ============================================================

print("\n[3/7] Chargement des horaires BAAC...")


def detecter_separateur(chemin) -> str:
    with open(chemin, "r", encoding="utf-8-sig") as f:
        premiere_ligne = f.readline()
    return ";" if ";" in premiere_ligne else ","

sep_detecte = detecter_separateur(CARACT_PATH)

df_caract = pd.read_csv(
    CARACT_PATH,
    sep=sep_detecte,
    encoding="utf-8-sig",
    usecols=["Num_Acc", "an", "mois", "jour", "hrmn"],
    low_memory=False,
)


df_caract["Num_Acc"] = (
    df_caract["Num_Acc"]
    .astype("string")
    .str.strip()
)


# ============================================================
# 7. CONSTRUCTION DE LA DATE BAAC
# ============================================================

df_caract["an"] = pd.to_numeric(
    df_caract["an"],
    errors="coerce"
)

df_caract["mois"] = pd.to_numeric(
    df_caract["mois"],
    errors="coerce"
)

df_caract["jour"] = pd.to_numeric(
    df_caract["jour"],
    errors="coerce"
)


df_caract["date"] = pd.to_datetime(
    df_caract["an"].astype("Int64").astype("string")
    + "-"
    + df_caract["mois"].astype("Int64").astype("string").str.zfill(2)
    + "-"
    + df_caract["jour"].astype("Int64").astype("string").str.zfill(2),
    errors="coerce"
)


# ============================================================
# 8. EXTRACTION DE L'HEURE
# ============================================================

df_caract["hrmn"] = (
    df_caract["hrmn"]
    .astype("string")
    .str.strip()
)


df_caract["heure"] = pd.to_datetime(
    df_caract["hrmn"],
    format="%H:%M",
    errors="coerce"
).dt.hour


# On conserve une seule ligne par accident.
#
# Pourquoi ?
#
# Le fichier caractéristiques doit normalement avoir
# une ligne par accident.
#
# Le drop_duplicates protège néanmoins contre une éventuelle
# duplication accidentelle.

df_caract = (
    df_caract[
        [
            "Num_Acc",
            "date",
            "heure"
        ]
    ]
    .drop_duplicates(subset="Num_Acc")
)


# ============================================================
# 9. JOINTURE ACCIDENT + HEURE
# ============================================================

print("\n[4/7] Jointure avec les horaires BAAC...")


df_acc = df_acc.merge(
    df_caract,
    on="Num_Acc",
    how="left"
)


nb_heure_connue = (
    df_acc["heure"]
    .notna()
    .sum()
)


pct_heure_connue = (
    nb_heure_connue
    / len(df_acc)
    * 100
)


print(
    f"[INFO] Heure connue : "
    f"{nb_heure_connue:,} / {len(df_acc):,} "
    f"({pct_heure_connue:.1f} %)"
)


# ============================================================
# 10. CONSTRUCTION DE LA DATE COMPLETE
# ============================================================

# La date issue de BAAC est utilisée en priorité.
#
# Si elle est absente, on peut reconstruire la date
# à partir de AAAAMMJJ venant de SQLite.

date_sqlite = pd.to_datetime(
    df_acc["AAAAMMJJ"],
    format="%Y%m%d",
    errors="coerce"
)


df_acc["date_jour"] = (
    df_acc["date"]
    .fillna(date_sqlite)
)


# ============================================================
# 11. JOUR DE LA SEMAINE
# ============================================================

JOURS_FR = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche"
}


df_acc["jour_semaine"] = (
    df_acc["date_jour"]
    .dt.dayofweek
    .map(JOURS_FR)
)


df_acc["is_weekend"] = (
    df_acc["date_jour"]
    .dt.dayofweek
    .isin([5, 6])
)


# ============================================================
# 12. MOIS
# ============================================================

MOIS_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre"
}


df_acc["mois"] = pd.to_numeric(
    df_acc["mois"],
    errors="coerce"
)


df_acc["mois_nom"] = (
    df_acc["mois"]
    .map(MOIS_FR)
)


# ============================================================
# 13. SAISON
# ============================================================

MOIS_VERS_SAISON = {

    12: "Hiver",
    1: "Hiver",
    2: "Hiver",

    3: "Printemps",
    4: "Printemps",
    5: "Printemps",

    6: "Été",
    7: "Été",
    8: "Été",

    9: "Automne",
    10: "Automne",
    11: "Automne"
}


df_acc["saison"] = (
    df_acc["mois"]
    .map(MOIS_VERS_SAISON)
)


# ============================================================
# 14. JOURS FERIES
# ============================================================

print("\n[5/7] Identification des jours fériés...")


if holidays is None:

    print(
        "\n[ERREUR] Le paquet 'holidays' n'est pas installé."
    )

    print(
        "Installez-le avec :"
    )

    print(
        "pip install holidays"
    )

    raise ImportError(
        "Le paquet Python 'holidays' est nécessaire."
    )


annees_valides = (
    df_acc["date_jour"]
    .dropna()
    .dt.year
    .astype(int)
    .unique()
)


jours_feries_fr = holidays.France(
    years=sorted(annees_valides)
)


df_acc["jour_ferie"] = (
    df_acc["date_jour"]
    .dt.date
    .isin(jours_feries_fr)
)


# Nom du jour férié
df_acc["nom_jour_ferie"] = (
    df_acc["date_jour"]
    .dt.date
    .map(jours_feries_fr)
)


print(
    f"[INFO] Accidents un jour férié : "
    f"{df_acc['jour_ferie'].sum():,} "
    f"({df_acc['jour_ferie'].mean() * 100:.1f} %)"
)


# ============================================================
# 15. EXPORT DU DATASET ENRICHI
# ============================================================

fichier_enrichi = (
    DOSSIER_CURATED
    / "accidents_analyse_temporelle.csv"
)


df_acc.to_csv(
    fichier_enrichi,
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


print(
    f"\n[OK] Dataset temporel créé :"
    f"\n     {fichier_enrichi}"
)


# ============================================================
# 16. ANALYSE PAR HEURE
# ============================================================

print("\n[6/7] Analyse par heure...")


accidents_par_heure = (
    df_acc
    .groupby("heure")
    .agg(
        nb_accidents=("Num_Acc", "size"),
        taux_grave_pct=("est_grave", "mean")
    )
    .reindex(range(24), fill_value=0)
)


accidents_par_heure["taux_grave_pct"] *= 100


accidents_par_heure = (
    accidents_par_heure
    .reset_index()
)


accidents_par_heure.to_csv(
    DOSSIER_CURATED
    / "temporel_accidents_par_heure.csv",
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


# Graphique
fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 5)
)


axes[0].bar(
    accidents_par_heure["heure"],
    accidents_par_heure["nb_accidents"]
)


axes[0].set_title(
    "Nombre d'accidents par heure"
)

axes[0].set_xlabel(
    "Heure de la journée"
)

axes[0].set_ylabel(
    "Nombre d'accidents"
)


axes[1].bar(
    accidents_par_heure["heure"],
    accidents_par_heure["taux_grave_pct"]
)


axes[1].set_title(
    "Taux d'accidents graves par heure"
)

axes[1].set_xlabel(
    "Heure de la journée"
)

axes[1].set_ylabel(
    "Taux d'accidents graves (%)"
)


plt.tight_layout()


plt.savefig(
    DOSSIER_DASHBOARD / "temporel_heure.png",
    dpi=150
)


plt.close()


# ============================================================
# 17. ANALYSE PAR JOUR DE LA SEMAINE
# ============================================================

print("Analyse par jour de la semaine...")


ORDRE_JOURS = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche"
]


accidents_par_jour = (
    df_acc
    .groupby("jour_semaine")
    .agg(
        nb_accidents=("Num_Acc", "size"),
        taux_grave_pct=("est_grave", "mean")
    )
    .reindex(ORDRE_JOURS)
)


accidents_par_jour["taux_grave_pct"] *= 100


accidents_par_jour = (
    accidents_par_jour
    .reset_index()
)


accidents_par_jour.to_csv(
    DOSSIER_CURATED
    / "temporel_accidents_par_jour.csv",
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 5)
)


axes[0].bar(
    accidents_par_jour["jour_semaine"],
    accidents_par_jour["nb_accidents"]
)


axes[0].set_title(
    "Nombre d'accidents par jour de la semaine"
)

axes[0].set_xlabel(
    "Jour"
)

axes[0].set_ylabel(
    "Nombre d'accidents"
)


axes[1].bar(
    accidents_par_jour["jour_semaine"],
    accidents_par_jour["taux_grave_pct"]
)


axes[1].set_title(
    "Taux d'accidents graves par jour"
)

axes[1].set_xlabel(
    "Jour"
)

axes[1].set_ylabel(
    "Taux d'accidents graves (%)"
)


plt.tight_layout()


plt.savefig(
    DOSSIER_DASHBOARD / "temporel_jour_semaine.png",
    dpi=150
)


plt.close()


# ============================================================
# 18. ANALYSE SEMAINE VS WEEK-END
# ============================================================

semaine_weekend = (
    df_acc
    .groupby("is_weekend")
    .agg(
        nb_accidents=("Num_Acc", "size"),
        taux_grave_pct=("est_grave", "mean")
    )
)


semaine_weekend["taux_grave_pct"] *= 100


semaine_weekend.index = semaine_weekend.index.map(
    {
        False: "Semaine",
        True: "Week-end"
    }
)


print("\n[RESULTAT] Semaine vs week-end :")

print(
    semaine_weekend.round(2)
)


# ============================================================
# 19. ANALYSE PAR MOIS
# ============================================================

print("\nAnalyse par mois...")


accidents_par_mois = (
    df_acc
    .groupby(["mois", "mois_nom"])
    .agg(
        nb_accidents=("Num_Acc", "size"),
        taux_grave_pct=("est_grave", "mean")
    )
    .reset_index()
    .sort_values("mois")
)


accidents_par_mois["taux_grave_pct"] *= 100


accidents_par_mois.to_csv(
    DOSSIER_CURATED
    / "temporel_accidents_par_mois.csv",
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 20. ANALYSE PAR SAISON
# ============================================================

print("Analyse par saison...")


ORDRE_SAISONS = [
    "Hiver",
    "Printemps",
    "Été",
    "Automne"
]


accidents_par_saison = (
    df_acc
    .groupby("saison")
    .agg(
        nb_accidents=("Num_Acc", "size"),
        taux_grave_pct=("est_grave", "mean")
    )
    .reindex(ORDRE_SAISONS)
    .reset_index()
)


accidents_par_saison["taux_grave_pct"] *= 100


accidents_par_saison.to_csv(
    DOSSIER_CURATED
    / "temporel_accidents_par_saison.csv",
    sep=";",
    index=False,
    encoding="utf-8-sig"
)


fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 5)
)


axes[0].bar(
    accidents_par_mois["mois_nom"],
    accidents_par_mois["nb_accidents"]
)


axes[0].set_title(
    "Nombre d'accidents par mois"
)

axes[0].set_xlabel(
    "Mois"
)

axes[0].set_ylabel(
    "Nombre d'accidents"
)

axes[0].tick_params(
    axis="x",
    rotation=45
)


axes[1].bar(
    accidents_par_saison["saison"],
    accidents_par_saison["taux_grave_pct"]
)


axes[1].set_title(
    "Taux d'accidents graves par saison"
)

axes[1].set_xlabel(
    "Saison"
)

axes[1].set_ylabel(
    "Taux d'accidents graves (%)"
)


plt.tight_layout()


plt.savefig(
    DOSSIER_DASHBOARD / "temporel_mois_saison.png",
    dpi=150
)


plt.close()


# ============================================================
# 21. ANALYSE JOURS FERIES
# ============================================================

print("Analyse des jours fériés...")


# ------------------------------------------------------------
# Construction du calendrier complet
# ------------------------------------------------------------

date_min = df_acc["date_jour"].min()
date_max = df_acc["date_jour"].max()


calendrier = pd.DataFrame(
    {
        "date_jour": pd.date_range(
            start=date_min,
            end=date_max,
            freq="D"
        )
    }
)


calendrier["jour_ferie"] = (
    calendrier["date_jour"]
    .dt.date
    .isin(jours_feries_fr)
)


# ------------------------------------------------------------
# Nombre réel de jours fériés / ordinaires
# ------------------------------------------------------------

nb_jours_feries = int(
    calendrier["jour_ferie"].sum()
)


nb_jours_ordinaires = int(
    (~calendrier["jour_ferie"]).sum()
)


# ------------------------------------------------------------
# Nombre d'accidents
# ------------------------------------------------------------

resume_feries = (
    df_acc
    .groupby("jour_ferie")
    .agg(
        nb_accidents=("Num_Acc", "size"),
        taux_grave_pct=("est_grave", "mean")
    )
)


resume_feries["taux_grave_pct"] *= 100


# Ajouter les lignes manquantes si nécessaire
for valeur in [False, True]:

    if valeur not in resume_feries.index:

        resume_feries.loc[
            valeur,
            "nb_accidents"
        ] = 0

        resume_feries.loc[
            valeur,
            "taux_grave_pct"
        ] = 0


resume_feries = (
    resume_feries
    .sort_index()
)


resume_feries.index = resume_feries.index.map(
    {
        False: "Jour ordinaire",
        True: "Jour férié"
    }
)


# ------------------------------------------------------------
# Accidents moyens par jour
# ------------------------------------------------------------

resume_feries["nombre_jours"] = [
    nb_jours_ordinaires,
    nb_jours_feries
]


resume_feries["accidents_par_jour"] = (
    resume_feries["nb_accidents"]
    / resume_feries["nombre_jours"]
)


resume_feries = resume_feries.round(2)


print("\n[RESULTAT] Jours fériés vs jours ordinaires :")

print(
    resume_feries
)


resume_feries.to_csv(
    DOSSIER_CURATED
    / "temporel_accidents_jours_feries.csv",
    sep=";",
    encoding="utf-8-sig"
)


# ------------------------------------------------------------
# Graphique
# ------------------------------------------------------------

fig, ax = plt.subplots(
    figsize=(7, 5)
)


resume_feries["accidents_par_jour"].plot(
    kind="bar",
    ax=ax
)


ax.set_title(
    "Nombre moyen d'accidents par jour"
)

ax.set_xlabel(
    ""
)

ax.set_ylabel(
    "Accidents / jour"
)


plt.tight_layout()


plt.savefig(
    DOSSIER_DASHBOARD
    / "temporel_jours_feries.png",
    dpi=150
)


plt.close()


# ============================================================
# 22. RESUME FINAL
# ============================================================

print("\n" + "=" * 70)
print("ANALYSE TEMPORELLE TERMINEE")
print("=" * 70)


print("\nFichiers créés dans data/curated :")

print(
    " - accidents_analyse_temporelle.csv"
)

print(
    " - temporel_accidents_par_heure.csv"
)

print(
    " - temporel_accidents_par_jour.csv"
)

print(
    " - temporel_accidents_par_mois.csv"
)

print(
    " - temporel_accidents_par_saison.csv"
)

print(
    " - temporel_accidents_jours_feries.csv"
)


print("\nGraphiques créés dans dashboard/ :")

print(
    " - temporel_heure.png"
)

print(
    " - temporel_jour_semaine.png"
)

print(
    " - temporel_mois_saison.png"
)

print(
    " - temporel_jours_feries.png"
)


print("\n[OK] Traitement terminé avec succès.")