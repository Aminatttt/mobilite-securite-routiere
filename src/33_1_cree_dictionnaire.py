from pathlib import Path
import pandas as pd
import gzip
import json

# --------------------------------------------------
# 1. CHEMINS DU PROJET
# --------------------------------------------------

RACINE = Path(__file__).resolve().parent.parent

DOSSIER_RAW = RACINE / "data" / "raw"
DOSSIER_CURATED = RACINE / "data" / "curated"

DOSSIER_CURATED.mkdir(parents=True, exist_ok=True)

FICHIER_SORTIE = DOSSIER_CURATED / "dictionnaire_donnees.csv"


# --------------------------------------------------
# 2. DETECTER LE TYPE D'UNE VARIABLE
# --------------------------------------------------

def detecter_type(serie):

    if pd.api.types.is_integer_dtype(serie):
        return "entier"

    if pd.api.types.is_float_dtype(serie):
        return "numerique"

    if pd.api.types.is_datetime64_any_dtype(serie):
        return "date"

    return "texte"


# --------------------------------------------------
# 3. LIRE LES FICHIERS
# --------------------------------------------------

def lire_fichier(fichier):

    try:

        # Vérifier si le fichier est compressé en GZIP
        with open(fichier, "rb") as f:
            est_gzip = f.read(2) == b"\x1f\x8b"

        # -------------------------
        # Fichier GZIP
        # -------------------------

        if est_gzip:

            print("      Fichier GZIP détecté")

            if fichier.suffix.lower() == ".csv":

                return pd.read_csv(
                    gzip.open(
                        fichier,
                        "rt",
                        encoding="utf-8",
                        errors="replace"
                    ),
                    sep=None,
                    engine="python",
                    nrows=1000
                )

            elif fichier.suffix.lower() == ".txt":

                return pd.read_csv(
                    gzip.open(
                        fichier,
                        "rt",
                        encoding="utf-8",
                        errors="replace"
                    ),
                    sep=";",
                    nrows=1000
                )

        # -------------------------
        # CSV normal
        # -------------------------

        if fichier.suffix.lower() == ".csv":

            return pd.read_csv(
                fichier,
                sep=None,
                engine="python",
                encoding_errors="replace",
                nrows=1000
            )

        # -------------------------
        # TXT
        # -------------------------

        elif fichier.suffix.lower() == ".txt":

            return pd.read_csv(
                fichier,
                sep=";",
                encoding_errors="replace",
                nrows=1000
            )

        # -------------------------
        # JSON
        # -------------------------

        elif fichier.suffix.lower() == ".json":

            with open(
                fichier,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as f:

                data = json.load(f)

            return pd.json_normalize(data)

    except Exception as e:

        print(f"Impossible de lire {fichier.name}")
        print(f"Erreur : {e}")

    return None


# --------------------------------------------------
# 4. CREATION DU DICTIONNAIRE
# --------------------------------------------------

lignes = []

print("======================================")
print("CREATION DU DICTIONNAIRE DE DONNEES")
print("======================================")


for dossier_source in DOSSIER_RAW.iterdir():

    if not dossier_source.is_dir():
        continue

    nom_source = dossier_source.name

    print(f"\nSource : {nom_source}")

    fichiers = list(dossier_source.rglob("*.csv"))
    fichiers += list(dossier_source.rglob("*.txt"))
    fichiers += list(dossier_source.rglob("*.json"))

    for fichier in fichiers:

        print(f"   Fichier : {fichier.name}")

        df = lire_fichier(fichier)

        if df is None:
            continue

        # Parcourir chaque colonne
        for colonne in df.columns:

            serie = df[colonne]

            valeurs = serie.dropna()

            exemple = None

            if not valeurs.empty:
                exemple = str(valeurs.iloc[0])

            lignes.append({

                "source": nom_source,

                "fichier": fichier.name,

                "variable": colonne,

                "type": detecter_type(serie),

                "nb_valeurs": len(serie),

                "nb_manquantes": int(serie.isna().sum()),

                "pct_manquantes":
                    round(
                        serie.isna().mean() * 100,
                        2
                    ),

                "exemple": exemple,

                "cle_jointure": "",

                "unite": "",

                "description": ""
            })


# --------------------------------------------------
# 5. SAUVEGARDER
# --------------------------------------------------

dictionnaire = pd.DataFrame(lignes)

if not dictionnaire.empty:

    dictionnaire = dictionnaire.sort_values(
        ["source", "fichier", "variable"]
    )

    dictionnaire.to_csv(
        FICHIER_SORTIE,
        index=False,
        encoding="utf-8-sig"
    )


print("\n======================================")
print("DICTIONNAIRE CREE")
print("======================================")

print(f"Fichier : {FICHIER_SORTIE}")

print(f"Variables trouvées : {len(dictionnaire)}")