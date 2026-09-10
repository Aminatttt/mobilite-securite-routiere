import pandas as pd
import os

def trouver_racine_projet(depart):
    dossier = depart
    while dossier != os.path.dirname(dossier):
        if os.path.exists(os.path.join(dossier, ".git")):
            return dossier
        dossier = os.path.dirname(dossier)
    raise FileNotFoundError("Racine du projet introuvable")

def trouver_dossier_plus_recent(chemin_source):
    sous_dossiers = [d for d in os.listdir(chemin_source) if os.path.isdir(os.path.join(chemin_source, d))]
    sous_dossiers.sort(reverse=True)
    return os.path.join(chemin_source, sous_dossiers[0])

dossier_script = os.path.dirname(os.path.abspath(__file__))
racine_projet = trouver_racine_projet(dossier_script)

dossier_baac_brut = os.path.join(racine_projet, "data", "raw", "baac")
dossier_dernier_run = trouver_dossier_plus_recent(dossier_baac_brut)
print("Dossier utilisé :", dossier_dernier_run)

chemin_caract = os.path.join(dossier_dernier_run, "Caract_2024.csv")
df = pd.read_csv(chemin_caract, sep=";", encoding="latin-1")

print("Nombre de lignes :", len(df))
print("Colonnes :", list(df.columns))
print("\nValeurs manquantes par colonne :")
print(df.isna().sum())
print("\nTypes de données :")
print(df.dtypes)

print("\n--- Échantillon de valeurs brutes ---")
print(df[['dep', 'lat', 'long']].head(10))
print("\nValeurs uniques de 'dep' :")
print(df['dep'].unique())

print("\n--- Nettoyage ---")

# 1. Filtrer sur Paris (dep = 75)
df_paris = df[df['dep'] == '75'].copy()
print(f"Lignes après filtrage Paris (dep=75) : {len(df_paris)}")

# 2. Corriger lat/long : remplacer la virgule par un point, puis convertir en nombre
df_paris['lat'] = df_paris['lat'].str.replace(',', '.').astype(float)
df_paris['long'] = df_paris['long'].str.replace(',', '.').astype(float)

print("\nTypes après correction :")
print(df_paris[['lat', 'long']].dtypes)
print("\nAperçu lat/long corrigées :")
print(df_paris[['lat', 'long']].head())


print("\n--- Chargement des autres fichiers BAAC ---")

chemin_lieux = os.path.join(dossier_dernier_run, "Lieux_2024.csv")
chemin_usagers = os.path.join(dossier_dernier_run, "Usagers_2024.csv")
chemin_vehicules = os.path.join(dossier_dernier_run, "Vehicules_2024.csv")

# --- Fichier vehicules-immatricule-baac-2024 EXCLU du pipeline ---
# Raison : clé "Id_accident" (ex: "67 230 442") sans correspondance avec "Num_Acc"
# (ex: 202400000011) des autres fichiers BAAC. Formats totalement différents,
# aucune table de correspondance trouvée sur data.gouv.fr. Décision d'équipe :
# le fichier "vehicules" standard (colonne catv = catégorie de véhicule) suffit.
# chemin_vehicules_immat = os.path.join(dossier_dernier_run, "vehicules-immatricule-baac-2024.csv")

df_lieux = pd.read_csv(chemin_lieux, sep=";", encoding="latin-1")
df_usagers = pd.read_csv(chemin_usagers, sep=";", encoding="latin-1")
df_vehicules = pd.read_csv(chemin_vehicules, sep=";", encoding="latin-1")

print("Lieux :", len(df_lieux), "lignes -", list(df_lieux.columns))
print("Usagers :", len(df_usagers), "lignes -", list(df_usagers.columns))
print("Vehicules :", len(df_vehicules), "lignes -", list(df_vehicules.columns))

# Filtrer chacun sur les accidents de Paris (via les Num_Acc déjà identifiés)
num_acc_paris = df_paris['Num_Acc'].unique()

df_lieux_paris = df_lieux[df_lieux['Num_Acc'].isin(num_acc_paris)].copy()
df_usagers_paris = df_usagers[df_usagers['Num_Acc'].isin(num_acc_paris)].copy()
df_vehicules_paris = df_vehicules[df_vehicules['Num_Acc'].isin(num_acc_paris)].copy()

print(f"\nLieux Paris : {len(df_lieux_paris)} lignes")
print(f"Usagers Paris : {len(df_usagers_paris)} lignes")
print(f"Vehicules Paris : {len(df_vehicules_paris)} lignes")

# df_vehicules_immat = pd.read_csv(chemin_vehicules_immat, sep=";", encoding="latin-1")
# print("Vehicules immatriculés :", len(df_vehicules_immat), "lignes -", list(df_vehicules_immat.columns))

print("\n--- Vérification doublons Num_Acc dans lieux ---")
print("Num_Acc uniques dans lieux (global) :", df_lieux['Num_Acc'].nunique())
print("Lignes totales dans lieux (global) :", len(df_lieux))
print("Num_Acc uniques dans lieux Paris :", df_lieux_paris['Num_Acc'].nunique())
print("Lignes dans lieux Paris :", len(df_lieux_paris))

# --- Test encodage UTF-8 sur vehicules-immatricule : plus nécessaire, fichier exclu ---
# df_vehicules_immat_test = pd.read_csv(chemin_vehicules_immat, sep=";", encoding="utf-8")
# print("\nColonnes avec encodage UTF-8 :", list(df_vehicules_immat_test.columns))

print("\n--- Analyse des doublons dans lieux Paris ---")
doublons = df_lieux_paris[df_lieux_paris.duplicated(subset='Num_Acc', keep=False)]
print("Nombre de lignes impliquées dans des doublons :", len(doublons))
print(doublons.sort_values('Num_Acc').head(10))

print("\n--- Traitement des lignes multiples par accident (intersections) ---")
compte_lignes = df_lieux_paris.groupby('Num_Acc').size()
df_lieux_paris['intersection'] = df_lieux_paris['Num_Acc'].map(compte_lignes) > 1

df_lieux_paris_unique = df_lieux_paris.drop_duplicates(subset='Num_Acc', keep='first')
print(f"Lignes après dédoublonnage (1 par accident) : {len(df_lieux_paris_unique)}")
print(f"Dont accidents en intersection : {df_lieux_paris_unique['intersection'].sum()}")

print("\n--- Vérification anomalies usagers/vehicules ---")
vrais_doublons_usagers = df_usagers_paris.duplicated().sum()
vrais_doublons_vehicules = df_vehicules_paris.duplicated().sum()
print("Lignes strictement identiques (usagers) :", vrais_doublons_usagers)
print("Lignes strictement identiques (vehicules) :", vrais_doublons_vehicules)

print("\nValeurs manquantes usagers :")
print(df_usagers_paris.isna().sum())
print("\nValeurs manquantes vehicules :")
print(df_vehicules_paris.isna().sum())

# --- Vehicules immatriculés : clé de jointure incompatible, fichier exclu du pipeline ---
# print("\n--- Vehicules immatriculés : vérification de la clé de jointure ---")
# df_vehicules_immat = pd.read_csv(chemin_vehicules_immat, sep=";", encoding="utf-8")
# print(df_vehicules_immat[['Id_accident']].head(10))
# print("\nType de Id_accident :", df_vehicules_immat['Id_accident'].dtype)
# print("\nType de Num_Acc (dans caracteristiques) :", df_paris['Num_Acc'].dtype)
# print("Exemple de Num_Acc :", df_paris['Num_Acc'].head(5).tolist())

print("\n--- Sauvegarde en CURATED ---")

dossier_curated = os.path.join(racine_projet, "data", "curated", "baac")
os.makedirs(dossier_curated, exist_ok=True)

df_paris.to_csv(os.path.join(dossier_curated, "caracteristiques_paris_2024.csv"), sep=";", index=False)
df_lieux_paris_unique.to_csv(os.path.join(dossier_curated, "lieux_paris_2024.csv"), sep=";", index=False)
df_usagers_paris.to_csv(os.path.join(dossier_curated, "usagers_paris_2024.csv"), sep=";", index=False)
df_vehicules_paris.to_csv(os.path.join(dossier_curated, "vehicules_paris_2024.csv"), sep=";", index=False)

print("Fichiers CURATED sauvegardés dans :", dossier_curated)
print("- caracteristiques_paris_2024.csv :", len(df_paris), "lignes")
print("- lieux_paris_2024.csv :", len(df_lieux_paris_unique), "lignes")
print("- usagers_paris_2024.csv :", len(df_usagers_paris), "lignes")
print("- vehicules_paris_2024.csv :", len(df_vehicules_paris), "lignes")