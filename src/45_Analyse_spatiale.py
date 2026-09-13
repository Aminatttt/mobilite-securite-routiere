import sqlite3
from pathlib import Path
import pandas as pd

#  DÉFINITION DES CHEMINS 
DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = (
    DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT
)
CHEMIN_DB = RACINE_PROJET / "data" / "mobilite_paris.db"
DOSSIER_SORTIE = RACINE_PROJET / "data" / "curated" / "analyse_spatiale"
DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

#  CONFIGURATION

DECIMALES_ZONE = 2
POIDS_GRAVITE = {1: 0, 2: 4, 3: 2, 4: 1}

# Nombre de zones les plus à risque à mettre en avant sur la carte
NB_ZONES_A_AFFICHER = 20
CENTRE_PARIS = (48.8566, 2.3522)

#  LECTURE DES DONNÉES DEPUIS SQLITE

def lire_accidents_geolocalises(connexion):
    
    requete = """
        SELECT
            f.Num_Acc,
            f.GEO,
            f.grav,
            g.lat,
            g.lon
        FROM FAIT_ACCIDENT f
        LEFT JOIN DIM_GEO g ON f.GEO = g.GEO
        WHERE f.GEO IS NOT NULL
    """

    df = pd.read_sql_query(requete, connexion)

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["grav"] = pd.to_numeric(df["grav"], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    df["poids_gravite"] = df["grav"].map(POIDS_GRAVITE).fillna(0)

    df_accidents = (
        df.groupby("Num_Acc", as_index=False)
        .agg(
            lat=("lat", "first"),
            lon=("lon", "first"),
            poids_gravite=("poids_gravite", "max"),
        )
    )

    return df_accidents

#  REGROUPEMENT EN ZONES ET CALCUL DU SCORE DE RISQUE

def calculer_zones_a_risque(df_accidents):

    df = df_accidents.copy()

    df["lat_zone"] = df["lat"].round(DECIMALES_ZONE)
    df["lon_zone"] = df["lon"].round(DECIMALES_ZONE)
    df["zone_id"] = df["lat_zone"].astype(str) + "_" + df["lon_zone"].astype(str)

    df["nb_tues"] = (df["poids_gravite"] == 4).astype(int)
    df["nb_blesses_hospitalises"] = (df["poids_gravite"] == 2).astype(int)
    df["nb_blesses_legers"] = (df["poids_gravite"] == 1).astype(int)

    df_zones = (
        df.groupby("zone_id", as_index=False)
        .agg(
            lat_centre=("lat_zone", "first"),
            lon_centre=("lon_zone", "first"),
            nb_accidents=("Num_Acc", "nunique"),
            nb_tues=("nb_tues", "sum"),
            nb_blesses_hospitalises=("nb_blesses_hospitalises", "sum"),
            nb_blesses_legers=("nb_blesses_legers", "sum"),
        )
    )

    df_zones["score_risque"] = (
        df_zones["nb_accidents"]
        + 3 * df_zones["nb_tues"]
        + 1 * df_zones["nb_blesses_hospitalises"]
    )

    df_zones = df_zones.sort_values("score_risque", ascending=False).reset_index(drop=True)
    df_zones["rang_risque"] = df_zones.index + 1

    return df_zones

#  GÉNÉRATION DE LA CARTE (folium, optionnel)

def generer_carte(df_accidents, df_zones):

    try:
        import folium
        from folium.plugins import HeatMap
    except ImportError:
        print("\n La librairie 'folium' n'est pas installée : la carte ne sera pas générée.")
        print("   Pour l'installer :  pip install folium")
        return None

    carte = folium.Map(location=CENTRE_PARIS, zoom_start=12, tiles="cartodbpositron")

    # --- Heatmap pondérée par la gravité (poids + 1 pour que même un
    #     accident sans blessé grave contribue un minimum) ---
    points_chaleur = [
        [row["lat"], row["lon"], row["poids_gravite"] + 1]
        for _, row in df_accidents.iterrows()
    ]
    HeatMap(points_chaleur, radius=10, blur=15, max_zoom=13).add_to(carte)

    # --- Marqueurs sur les zones les plus à risque ---
    top_zones = df_zones.head(NB_ZONES_A_AFFICHER)

    score_max = top_zones["score_risque"].max() if not top_zones.empty else 1

    for _, zone in top_zones.iterrows():

        intensite = zone["score_risque"] / score_max if score_max else 0

        if intensite > 0.66:
            couleur = "red"
        elif intensite > 0.33:
            couleur = "orange"
        else:
            couleur = "green"

        popup_html = (
            f"<b>Zone (rang {int(zone['rang_risque'])})</b><br>"
            f"Score de risque : {zone['score_risque']}<br>"
            f"Accidents : {zone['nb_accidents']}<br>"
            f"Tués : {zone['nb_tues']}<br>"
            f"Blessés hospitalisés : {zone['nb_blesses_hospitalises']}<br>"
            f"Blessés légers : {zone['nb_blesses_legers']}"
        )

        folium.CircleMarker(
            location=[zone["lat_centre"], zone["lon_centre"]],
            radius=6 + 10 * intensite,
            color=couleur,
            fill=True,
            fill_color=couleur,
            fill_opacity=0.6,
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(carte)

    chemin_carte = DOSSIER_SORTIE / "carte_zones_a_risque.html"
    carte.save(str(chemin_carte))

    return chemin_carte

#  TÂCHE 45 : Analyse_spatiale

def analyser_spatialement():
    print("=" * 80)
    print("TÂCHE 45 — ANALYSE SPATIALE (CARTE, ZONES À RISQUE)")
    print("=" * 80)

    if not CHEMIN_DB.exists():
        raise FileNotFoundError(f" La base SQLite est introuvable : {CHEMIN_DB} " )

    print(f"\n Base SQLite : {CHEMIN_DB}")
    print(f" Sorties     : {DOSSIER_SORTIE}")

    connexion = sqlite3.connect(CHEMIN_DB)
    try:
        #  LECTURE DES ACCIDENTS GÉOLOCALISÉS

        print("\n" + "-" * 80)
        print("1. LECTURE DES ACCIDENTS GÉOLOCALISÉS")
        print("-" * 80)

        df_accidents = lire_accidents_geolocalises(connexion)
        print(f"  Accidents géolocalisés (avec lat/lon valides) : {len(df_accidents)}")

        if df_accidents.empty:
            print("   Aucun accident géolocalisé trouvé — vérifier GEO dans FAIT_ACCIDENT / DIM_GEO.")
            return

        #  REGROUPEMENT EN ZONES À RISQUE

        print("\n" + "-" * 80)
        print(f"2. CALCUL DES ZONES À RISQUE (grille ~{DECIMALES_ZONE} décimales)")
        print("-" * 80)

        df_zones = calculer_zones_a_risque(df_accidents)

        print(f"  Nombre de zones distinctes : {len(df_zones)}")
        print(f"\n  Top {min(10, len(df_zones))} zones les plus à risque :")
        print(
            df_zones.head(10)[
                ["rang_risque", "zone_id", "nb_accidents", "nb_tues",
                 "nb_blesses_hospitalises", "nb_blesses_legers", "score_risque"]
            ].to_string(index=False)
        )

        chemin_zones = DOSSIER_SORTIE / "zones_a_risque.csv"
        df_zones.to_csv(chemin_zones, sep=";", index=False, encoding="utf-8")
        print(f"\n   Classement des zones sauvegardé : {chemin_zones}")

        #  GÉNÉRATION DE LA CARTE

        print("\n" + "-" * 80)
        print("3. GÉNÉRATION DE LA CARTE INTERACTIVE")
        print("-" * 80)

        chemin_carte = generer_carte(df_accidents, df_zones)

        if chemin_carte:
            print(f"   Carte sauvegardée : {chemin_carte}")
            print("     (à ouvrir dans un navigateur)")

        # ============ RÉSUMÉ ====================

        print("\n" + "=" * 80)
        print("RÉSUMÉ")
        print("=" * 80)
        print(f"  Total accidents analysés   : {len(df_accidents)}")
        print(f"  Total tués                 : {int(df_accidents['poids_gravite'].eq(4).sum())}")
        print(f"  Total blessés hospitalisés : {int(df_accidents['poids_gravite'].eq(2).sum())}")
        print(f"  Total blessés légers       : {int(df_accidents['poids_gravite'].eq(1).sum())}")
        print(f"  Nombre de zones            : {len(df_zones)}")
        print(f"  Zone la plus à risque      : {df_zones.iloc[0]['zone_id']} "
              f"(score {df_zones.iloc[0]['score_risque']})")

        print("\n ANALYSE SPATIALE TERMINÉE AVEC SUCCÈS.")
    finally:
        connexion.close()

if __name__ == "__main__":
    analyser_spatialement()