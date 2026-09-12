"""
24_1_nettoyer_trafic.py — ETL Trafic Routier (Agrégation Hebdomadaire)
========================================================================
Traite les données horaires brutes de trafic et produit UN SEUL fichier
CURATED final, agrégé par capteur (iu_ac) et par semaine, sous la limite
GitHub (100 Mo).

CORRECTION : la version précédente sauvegardait un fichier CSV séparé
par semaine RAW traitée (~260 fichiers). Cette version accumule tous les
résultats en mémoire et ne sauvegarde qu'un seul fichier final.
"""
import sys
import io
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings('ignore')

try:
    if hasattr(sys.stdout, 'buffer') and sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

from utils_log import creer_logger

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
logger = creer_logger("nettoyer_trafic", SCRIPT_DIR)

DOSSIER_TRAFIC_BRUT = BASE_DIR / "data" / "raw" / "trafic"
DOSSIER_CURATED = BASE_DIR / "data" / "curated" / "trafic"
DOSSIER_CURATED.mkdir(parents=True, exist_ok=True)

SEUIL_CAPTEUR_HS = 0.30


def process_file(file_path: Path):
    """Nettoie et agrège UN fichier hebdomadaire de trafic. Retourne un DataFrame (ne sauvegarde rien)."""
    try:
        df = pd.read_csv(
            file_path, sep=';', encoding='utf-8',
            low_memory=False, on_bad_lines='skip'
        )

        if 'dessin' in df.columns:
            df = df.drop(columns=['dessin'])
        for col in ['q', 'k']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'iu_ac' not in df.columns or 't_1h' not in df.columns:
            logger.warning(f"Colonnes essentielles manquantes dans {file_path.name}, fichier ignoré")
            return None

        df['iu_ac'] = df['iu_ac'].astype('category')
        df['t_1h'] = pd.to_datetime(df['t_1h'], errors='coerce')

        stats = df.groupby('iu_ac', observed=True).agg(
            q_missing_rate=('q', lambda s: s.isna().mean()),
            q_median=('q', 'median'),
            k_median=('k', 'median')
        )

        capteurs_ok = stats[stats['q_missing_rate'] <= SEUIL_CAPTEUR_HS].index
        df = df[df['iu_ac'].isin(capteurs_ok)].copy()

        df['q_missing'] = df['q'].isna().astype(int)
        df['k_missing'] = df['k'].isna().astype(int)

        df['q'] = df['q'].fillna(df['iu_ac'].map(stats['q_median'])).fillna(df['q'].median())
        df['k'] = df['k'].fillna(df['iu_ac'].map(stats['k_median'])).fillna(df['k'].median())

        agg_dict = {
            'q_total': ('q', 'sum'),
            'q_moyen': ('q', 'mean'),
            'k_moyen': ('k', 'mean'),
            'nb_heures': ('q', 'count'),
            'q_missing_rate': ('q_missing', 'mean'),
            'k_missing_rate': ('k_missing', 'mean'),
            't_debut': ('t_1h', 'min'),
            't_fin': ('t_1h', 'max'),
        }

        df_hebdo = df.groupby('iu_ac', observed=True).agg(**agg_dict).reset_index()
        df_hebdo['fichier_source'] = file_path.name
        return df_hebdo

    except Exception as e:
        logger.error(f"Erreur sur {file_path.name} : {e}")
        return None


def executer():
    logger.info("=== Debut Etape 24.1 : Nettoyage et Agregation du Trafic ===")
    fichiers = list(DOSSIER_TRAFIC_BRUT.rglob("*.txt")) + list(DOSSIER_TRAFIC_BRUT.rglob("*.csv"))
    if not fichiers:
        logger.warning(f"Aucun fichier brut trouve dans {DOSSIER_TRAFIC_BRUT}")
        return

    logger.info(f"{len(fichiers)} fichiers hebdomadaires a traiter")

    resultats = []
    for i, f in enumerate(fichiers, 1):
        df_resultat = process_file(f)
        if df_resultat is not None:
            resultats.append(df_resultat)
        if i % 20 == 0:
            logger.info(f"  ... {i}/{len(fichiers)} fichiers traites")

    if not resultats:
        logger.error("Aucun resultat produit, arret")
        return

    df_final = pd.concat(resultats, ignore_index=True)
    logger.info(f"Fusion terminee : {len(df_final):,} lignes (capteur x semaine)")

    chemin_sortie = DOSSIER_CURATED / "trafic_2020_2024_agrege_semaine_clean.csv"
    df_final.to_csv(chemin_sortie, sep=";", index=False, encoding='utf-8-sig')
    logger.info(f"Fichier final unique sauvegarde : {chemin_sortie} ({len(df_final):,} lignes)")

    logger.info("=== Fin Etape 24.1 : Trafic Termine ===")


if __name__ == "__main__":
    executer()