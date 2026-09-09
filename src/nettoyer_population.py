import os
import pandas as pd

# 1. Définir les chemins d'accès aux dossiers
dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_entree = os.path.join(dossier_script, "..", "data", "raw", "population")
dossier_sortie = os.path.join(dossier_script, "..", "data", "processed")

# S'assurer que le dossier de sortie existe
os.makedirs(dossier_sortie, exist_ok=True)

print("Début du nettoyage des données de population...")

try:
    # 2. Charger le fichier brut
    chemin_fichier = os.path.join(dossier_entree, "population.csv") 
    df = pd.read_csv(chemin_fichier, sep=';', low_memory=False)
    print("Fichier chargé avec succès !")

    # 3. Filtrer sur Paris (code département 75)
    df_paris = df[df['dep'] == '75']
    print(f"Filtrage terminé : {len(df_paris)} lignes conservées pour Paris.")

    # 4. Sauvegarder le résultat propre
    chemin_sortie = os.path.join(dossier_sortie, "population_paris_nettoye.csv")
    df_paris.to_csv(chemin_sortie, index=False, sep=',')
    print(f"Fichier propre sauvegardé ici : {chemin_sortie}")

except Exception as e:
    print(f"Erreur lors du traitement : {e}")
