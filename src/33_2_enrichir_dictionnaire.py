from pathlib import Path
import pandas as pd


# ======================================
# CHEMINS
# ======================================

RACINE = Path(__file__).resolve().parent.parent

FICHIER_ENTREE = (
    RACINE
    / "data"
    / "curated"
    / "dictionnaire_donnees.csv"
)

FICHIER_SORTIE = (
    RACINE
    / "data"
    / "curated"
    / "dictionnaire_donnees_enrichi.csv"
)


# ======================================
# LECTURE DU DICTIONNAIRE
# ======================================

print("======================================")
print("ENRICHISSEMENT DU DICTIONNAIRE")
print("======================================")

print(f"\nLecture : {FICHIER_ENTREE}")

df = pd.read_csv(
    FICHIER_ENTREE,
    encoding="utf-8-sig"
)

print(f"Variables trouvées : {len(df)}")


# ======================================
# PREPARATION DES COLONNES TEXTE
# ======================================

# Ces colonnes peuvent contenir des valeurs vides.
# On les transforme en texte pour pouvoir ajouter
# les informations d'enrichissement.

df["cle_jointure"] = (
    df["cle_jointure"]
    .fillna("")
    .astype(str)
)

df["unite"] = (
    df["unite"]
    .fillna("")
    .astype(str)
)

df["description"] = (
    df["description"]
    .fillna("")
    .astype(str)
)


# ======================================
# CLES DE JOINTURE
# ======================================

cles = {

    "Num_Acc":
        "OUI - identifiant accident",

    "Id_Accident":
        "A vérifier - correspondance accident",

    "iu_ac":
        "OUI - identifiant tronçon / arc",

    "AAAAMMJJ":
        "OUI - clé de date",

    "GEO":
        "OUI - code géographique"
}


# ======================================
# UNITES
# ======================================

unites = {

    "q":
        "véhicules/heure",

    "k":
        "%",

    "RR":
        "mm",

    "TN":
        "°C",

    "TX":
        "°C",

    "TM":
        "°C",

    "TAMPLI":
        "°C"
}


# ======================================
# DESCRIPTIONS
# ======================================

descriptions = {

    # ----------------------------------
    # BAAC
    # ----------------------------------

    "Num_Acc":
        "Identifiant unique de l'accident",

    "lum":
        "Conditions de luminosité au moment de l'accident",

    "atm":
        "Conditions atmosphériques au moment de l'accident",

    "col":
        "Type de collision",

    "lat":
        "Latitude du lieu de l'accident",

    "long":
        "Longitude du lieu de l'accident",

    "grav":
        "Gravité de l'accident ou de l'usager",

    "catu":
        "Catégorie de l'usager",

    "secu1":
        "Premier équipement de sécurité utilisé",

    "secu2":
        "Deuxième équipement de sécurité",

    "secu3":
        "Troisième équipement de sécurité",


    # ----------------------------------
    # VEHICULES IMMATRICULES
    # ----------------------------------

    "Id_Accident":
        "Identifiant de l'accident dans le fichier des véhicules immatriculés",


    # ----------------------------------
    # TRAFIC
    # ----------------------------------

    "iu_ac":
        "Identifiant de l'arc ou du tronçon routier",

    "q":
        "Débit de circulation",

    "k":
        "Taux d'occupation du trafic",

    "etat_trafic":
        "État du trafic",

    "etat_barre":
        "État de la barre ou du capteur",

    "t_1h":
        "Horodatage de la mesure de trafic",


    # ----------------------------------
    # METEO
    # ----------------------------------

    "AAAAMMJJ":
        "Date de la mesure météorologique au format AAAAMMJJ",

    "RR":
        "Quantité de précipitations",

    "TN":
        "Température minimale",

    "TX":
        "Température maximale",

    "TM":
        "Température moyenne",

    "TAMPLI":
        "Amplitude thermique",


    # ----------------------------------
    # POPULATION
    # ----------------------------------

    "GEO":
        "Code géographique",

    "GEO_OBJECT":
        "Type d'objet géographique",

    "FREQ":
        "Fréquence de la donnée",

    "POPREF_MEASURE":
        "Type de mesure de population",

    "TIME_PERIOD":
        "Période de référence",

    "OBS_VALUE":
        "Valeur observée de la population"
}


# ======================================
# ENRICHISSEMENT
# ======================================

print("\nEnrichissement en cours...")

for index, ligne in df.iterrows():

    variable = str(ligne["variable"])


    # ----------------------------------
    # CLE DE JOINTURE
    # ----------------------------------

    if variable in cles:

        df.at[
            index,
            "cle_jointure"
        ] = cles[variable]


    # ----------------------------------
    # UNITE
    # ----------------------------------

    if variable in unites:

        df.at[
            index,
            "unite"
        ] = unites[variable]


    # ----------------------------------
    # DESCRIPTION
    # ----------------------------------

    if variable in descriptions:

        df.at[
            index,
            "description"
        ] = descriptions[variable]


# ======================================
# SAUVEGARDE
# ======================================

df.to_csv(
    FICHIER_SORTIE,
    index=False,
    encoding="utf-8-sig"
)


# ======================================
# RESULTAT
# ======================================

print("\n======================================")
print("DICTIONNAIRE ENRICHI")
print("======================================")

print(f"Fichier : {FICHIER_SORTIE}")

print(f"Variables : {len(df)}")

print("\nInformations ajoutées :")

print("- Clés de jointure")
print("- Unités")
print("- Descriptions")

print("\n======================================")
print("✅ TERMINÉ")
print("======================================")