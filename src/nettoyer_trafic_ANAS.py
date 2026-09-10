import pandas as pd
import os
import glob

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

dossier_trafic_brut = os.path.join(racine_projet, "data", "raw", "trafic")
dossier_dernier_run = trouver_dossier_plus_recent(dossier_trafic_brut)
print("Dossier utilisé :", dossier_dernier_run)

motif_recherche = os.path.join(dossier_dernier_run, "**", "*.txt")
fichiers_txt = glob.glob(motif_recherche, recursive=True)
print(f"Nombre de fichiers .txt trouvés : {len(fichiers_txt)}")

colonnes_utiles = ["iu_ac", "t_1h", "q", "k", "etat_trafic", "etat_barre"]

liste_df = []
for i, fichier in enumerate(fichiers_txt, 1):
    try:
        df_temp = pd.read_csv(fichier, sep=";", encoding="utf-8",
                               usecols=colonnes_utiles, low_memory=False)
        liste_df.append(df_temp)
        if i % 20 == 0:
            print(f"  ... {i}/{len(fichiers_txt)} fichiers chargés")
    except Exception as e:
        print(f"  -> ERREUR sur {os.path.basename(fichier)} : {e}")

df = pd.concat(liste_df, ignore_index=True)
print(f"\nTotal après concaténation : {len(df):,} lignes, {df.shape[1]} colonnes")

df["t_1h"] = pd.to_datetime(df["t_1h"], errors="coerce")
print("Dates invalides après conversion :", df["t_1h"].isna().sum())

print("\nValeurs manquantes par colonne :")
print(df.isna().sum())

nb_doublons = df.duplicated().sum()
print(f"\nLignes strictement identiques (doublons) : {nb_doublons:,}")
df = df.drop_duplicates()
print(f"Lignes après suppression des doublons : {len(df):,}")

# --- 7. Agrégation hebdomadaire + sauvegarde en CURATED ---
print("\n--- Agrégation hebdomadaire par tronçon (pour CURATED) ---")
df["semaine"] = df["t_1h"].dt.to_period("W").astype(str)
df_agrege = df.groupby(["iu_ac", "semaine"]).agg(
    q_moyen=("q", "mean"),
    k_moyen=("k", "mean"),
    nb_mesures=("q", "count")
).reset_index()
print(f"Lignes après agrégation hebdomadaire : {len(df_agrege):,}")

dossier_curated = os.path.join(racine_projet, "data", "curated", "trafic")
os.makedirs(dossier_curated, exist_ok=True)

chemin_agrege = os.path.join(dossier_curated, "trafic_2020_2024_agrege_semaine.csv")
df_agrege.to_csv(chemin_agrege, sep=";", index=False)
print(f"Version agrégée sauvegardée dans : {chemin_agrege}")