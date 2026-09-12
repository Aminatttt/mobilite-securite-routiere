import pandas as pd
import os


def trouver_racine_projet(depart):
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, "data")):
            return dossier
        dossier = os.path.dirname(dossier)

    raise FileNotFoundError("Racine du projet introuvable (aucun dossier 'data' trouvé "
        "en remontant depuis : " + depart + ")"
    )

def trouver_dossier_plus_recent(chemin_source):
    sous_dossiers = [
        d for d in os.listdir(chemin_source)
        if os.path.isdir(os.path.join(chemin_source, d))
    ]
    sous_dossiers.sort(reverse=True)
    return os.path.join(chemin_source, sous_dossiers[0])


dossier_script = os.path.dirname(os.path.abspath(__file__))
racine_projet = trouver_racine_projet(dossier_script)


# ================== TROUVER AUTOMATIQUEMENT LE DOSSIER RAW/POPULATION =============
dossier_raw_population = os.path.join(racine_projet, "data", "raw", "population")

if not os.path.exists(dossier_raw_population):
    raise FileNotFoundError("Le dossier data/raw/population est introuvable.")

dossier_raw = trouver_dossier_plus_recent(dossier_raw_population)

print("Dossier utilisé :", dossier_raw)


# ====================DOSSIER CURATED (créé automatiquement s'il n'existe pas)=====================

dossier_curated_racine = os.path.join(racine_projet, "data", "curated")
os.makedirs(dossier_curated_racine, exist_ok=True)


# =============================== RECHERCHE DES FICHIERS DATA ET METADATA =================================

fichier_data = None
fichier_metadata = None

for nom in os.listdir(dossier_raw):
    nom_lower = nom.lower()

    if not nom_lower.endswith(".csv"):
        continue

    if "metadata" in nom_lower:
        fichier_metadata = os.path.join(dossier_raw, nom)
    elif "data" in nom_lower:
        fichier_data = os.path.join(dossier_raw, nom)

if fichier_data is None or fichier_metadata is None:
    raise FileNotFoundError("Fichier data ou metadata introuvable dans data/raw/population.")

print("Fichier data     :", fichier_data)
print("Fichier metadata :", fichier_metadata)


# ============================= LECTURE DES FICHIERS ==================================

df = pd.read_csv(fichier_data, sep=";", encoding="utf-8", dtype=str)
metadata = pd.read_csv(fichier_metadata, sep=";", encoding="utf-8", dtype=str)

print("\n--- Aperçu data ---")
print(df.head())
print("\nDimensions data (avant filtrage) :", df.shape)

print("\n--- Aperçu metadata ---")
print(metadata.head())
print("\nVariables présentes dans metadata :", metadata["COD_VAR"].unique())


# =================================== NETTOYAGE DES ESPACES =============================================

df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
metadata = metadata.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

# =================================== CORRECTION DES TYPEs ========================================

print("\n========== CORRECTION DES TYPES ==========")

df["GEO"] = df["GEO"].astype("string")
df["GEO_OBJECT"] = df["GEO_OBJECT"].astype("string")
df["FREQ"] = df["FREQ"].astype("string")
df["POPREF_MEASURE"] = df["POPREF_MEASURE"].astype("string")

df["TIME_PERIOD"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")

print(df.dtypes.to_string())


# ================================ DONNÉES MANQUANTES ET DOUBLONS =======================================

print("\n========== DONNÉES MANQUANTES ==========")
print(df.isna().sum())

print("\n========== DOUBLONS ==========")
doublons = df.duplicated().sum()
print("Nombre de doublons exacts :", doublons)
df = df.drop_duplicates()

# ====================================== VALEURS NÉGATIVES ==========================================

print("\n========== VALEURS NEGATIVES ==========")
nb_negatives = (df["OBS_VALUE"] < 0).sum()
if nb_negatives > 0:
    print(f"OBS_VALUE : {nb_negatives} valeurs négatives -> remplacées par NaN")
    df.loc[df["OBS_VALUE"] < 0, "OBS_VALUE"] = pd.NA
else:
    print("Aucune valeur négative détectée.")


# ================================== DÉCODAGE VIA METADATA ========================================

print("\n========== DÉCODAGE VIA METADATA ==========")

def construire_dictionnaire(metadata, code_var):

    sous_table = metadata[metadata["COD_VAR"] == code_var]
    return dict(zip(sous_table["COD_MOD"], sous_table["LIB_MOD"]))

dico_geo = construire_dictionnaire(metadata, "GEO")
dico_mesure = construire_dictionnaire(metadata, "POPREF_MEASURE")
dico_freq = construire_dictionnaire(metadata, "FREQ")

df["GEO_LIB"] = df["GEO"].map(dico_geo)
df["POPREF_MEASURE_LIB"] = df["POPREF_MEASURE"].map(dico_mesure)
df["FREQ_LIB"] = df["FREQ"].map(dico_freq)

print("Exemple après décodage :")
print(df[["GEO", "GEO_LIB", "GEO_OBJECT", "POPREF_MEASURE", "POPREF_MEASURE_LIB", "OBS_VALUE"]].head())

non_decodes = df["GEO_LIB"].isna().sum()
print(f"\nCodes GEO non trouvés dans metadata : {non_decodes}")



#  ============================================ FILTRAGE ==========================================

print("\n========== FILTRE PARIS ==========")

codes_arrondissements_paris = [f"751{i:02d}" for i in range(1, 21)]

condition_paris = (
    ((df["GEO_OBJECT"] == "DEP") & (df["GEO"] == "75")) |      
    ((df["GEO_OBJECT"] == "ARR") & (df["GEO"] == "751")) |    
    ((df["GEO_OBJECT"] == "COM") & (df["GEO"] == "75056")) |  
    ((df["GEO_OBJECT"] == "ARM") & (df["GEO"].isin(codes_arrondissements_paris)))  
)

df_paris = df[condition_paris].copy()

print("Dimensions après filtrage Paris :", df_paris.shape)
print("\nRépartition par type géographique (GEO_OBJECT) :")
print(df_paris["GEO_OBJECT"].value_counts())
print("\nLibellés retenus :")
print(sorted(df_paris["GEO_LIB"].unique()))


# ================================ SAUVEGARDE EN CURATED =============================

print("\n--- Sauvegarde en CURATED ---")

dossier_curated = os.path.join(racine_projet, "data", "curated", "population")
os.makedirs(dossier_curated, exist_ok=True)

chemin_clean = os.path.join(dossier_curated, "population_paris_2023.csv")
df_paris.to_csv(chemin_clean, sep=";", index=False, encoding="utf-8")

print("Fichier CURATED sauvegardé dans :", dossier_curated)
print("- population_paris_2023.csv :", len(df_paris), "lignes")

print("\n Traitement population terminé.")