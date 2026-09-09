import pandas as pd
import os

def nettoyer_trafic():
    print("Début du nettoyage des données de trafic...")
    
    # 1. Charger le fichier brut de trafic
    input_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw', 'trafic', 'trafic.csv')
    
    try:
        df = pd.read_csv(input_path)
        print("Fichier chargé avec succès !")
    except Exception as e:
        print(f"Erreur lors du chargement : {e}")
        return

    # Afficher les colonnes pour vérifier leur nom exact
    print("Colonnes disponibles dans le fichier :", df.columns.tolist())

    # ' (emplacez 'type' par le nom exact de colonne )
    if 'type' in df.columns:
        df = df[df['type'] != 'dessin']
    else:
        print("Attention : la colonne 'type' n'a pas été trouvée directement.")

    # 3.  (supprimer les lignes vides)
    colonnes_a_verifier = [c for c in ['q', 'k'] if c in df.columns]
    if colonnes_a_verifier:
        df = df.dropna(subset=colonnes_a_verifier)

    # 4. Créer le dossier de sortie s'il n'existe pas 
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
    os.makedirs(output_dir, exist_ok=True)
    
    # 5. Enregistrer le fichier propre
    output_path = os.path.join(output_dir, 'trafic_nettoye.csv')
    df.to_csv(output_path, index=False)
    print(f"Nettoyage terminé avec succès ! Fichier sauvegardé dans : {output_path}")

if __name__ == "__main__":
    nettoyer_trafic()
