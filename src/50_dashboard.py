"""
===============================================================================
TÂCHE 50 — DASHBOARD (4 KPI, carte, filtres, page limites)
===============================================================================
Dashboard interactif Streamlit s'appuyant sur data/mobilite_paris.db
(table FAIT_ACCIDENT_ENRICHI, produite en tâches 36-38).

Lancer avec :
    pip install streamlit streamlit-folium folium
    streamlit run src/50_dashboard.py
===============================================================================
"""

from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st

try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_DISPONIBLE = True
except ImportError:
    FOLIUM_DISPONIBLE = False

# -----------------------------------------------------------------------
# CHEMINS
# -----------------------------------------------------------------------
DOSSIER_SCRIPT = Path(__file__).resolve().parent
RACINE_PROJET = DOSSIER_SCRIPT.parent if DOSSIER_SCRIPT.name == "src" else DOSSIER_SCRIPT
DB_PATH = RACINE_PROJET / "data" / "mobilite_paris.db"

st.set_page_config(page_title="Sécurité routière à Paris", layout="wide")


# -----------------------------------------------------------------------
# CHARGEMENT DES DONNÉES (mis en cache pour ne pas recharger à chaque clic)
# -----------------------------------------------------------------------
@st.cache_data
def charger_donnees() -> pd.DataFrame:
    if not DB_PATH.exists():
        st.error(f"Base introuvable : {DB_PATH}")
        st.stop()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        """
        SELECT Num_Acc, annee, mois, grav, GEO, com,
               meteo_precipitations, q_moyen
        FROM FAIT_ACCIDENT_ENRICHI
        """,
        conn,
    )
    conn.close()
    df["grav"] = pd.to_numeric(df["grav"], errors="coerce")
    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["meteo_precipitations"] = pd.to_numeric(df["meteo_precipitations"], errors="coerce")
    df["q_moyen"] = pd.to_numeric(df["q_moyen"], errors="coerce")

    # GEO est stocké au format "lat_lon" (ex: "48.8693_2.3543"), tel
    # qu'extrait en tâche 36 depuis geo_point_2d. On le reconstruit en
    # deux colonnes numériques lat/lon pour pouvoir tracer la carte.
    coords = df["GEO"].astype("string").str.split("_", n=1, expand=True)
    if coords.shape[1] == 2:
        df["lat"] = pd.to_numeric(coords[0], errors="coerce")
        df["lon"] = pd.to_numeric(coords[1], errors="coerce")
    else:
        df["lat"] = pd.NA
        df["lon"] = pd.NA

    # condition_pluie : mêmes seuils que la tâche 46 (0 / 0-5 / >5 mm)
    def categoriser_pluie(precip):
        if pd.isna(precip):
            return "Inconnu"
        if precip <= 0:
            return "Temps Sec (0 mm)"
        if precip <= 5:
            return "Pluie Léger (0-5 mm)"
        return "Pluie Forte (>5 mm)"

    df["condition_pluie"] = df["meteo_precipitations"].apply(categoriser_pluie)

    # niveau_trafic : approximation par terciles (les seuils exacts de la
    # tâche 47 ne sont pas dans ce fichier ; à harmoniser avec wissal si
    # les catégories doivent matcher exactement celles de la tâche 47)
    q_valides = df["q_moyen"].dropna()
    if len(q_valides) > 0:
        seuil_bas, seuil_haut = q_valides.quantile([0.33, 0.66])
    else:
        seuil_bas, seuil_haut = 0, 0

    def categoriser_trafic(q):
        if pd.isna(q):
            return "Inconnu"
        if q <= seuil_bas:
            return "Trafic Fluide (Faible)"
        if q <= seuil_haut:
            return "Trafic Modéré"
        return "Trafic Dense / Saturé"

    df["niveau_trafic"] = df["q_moyen"].apply(categoriser_trafic)

    return df


df = charger_donnees()

# -----------------------------------------------------------------------
# BARRE LATÉRALE — FILTRES
# -----------------------------------------------------------------------
st.sidebar.header("Filtres")

annees_dispo = sorted(df["annee"].dropna().unique().astype(int))
annees_choisies = st.sidebar.multiselect(
    "Année(s)", annees_dispo, default=annees_dispo
)

meteo_dispo = sorted(df["condition_pluie"].dropna().unique()) if "condition_pluie" in df.columns else []
meteo_choisie = st.sidebar.multiselect("Météo", meteo_dispo, default=meteo_dispo)

trafic_dispo = sorted(df["niveau_trafic"].dropna().unique()) if "niveau_trafic" in df.columns else []
trafic_choisi = st.sidebar.multiselect("Niveau de trafic", trafic_dispo, default=trafic_dispo)

df_filtre = df[df["annee"].isin(annees_choisies)]
if meteo_choisie:
    df_filtre = df_filtre[df_filtre["condition_pluie"].isin(meteo_choisie)]
if trafic_choisi:
    df_filtre = df_filtre[df_filtre["niveau_trafic"].isin(trafic_choisi)]

# -----------------------------------------------------------------------
# ONGLETS
# -----------------------------------------------------------------------
onglet_vue, onglet_carte, onglet_limites = st.tabs(
    ["Vue d'ensemble", "Carte", "Limites connues"]
)

# -------------------------------------------------------------------
# ONGLET 1 — KPI + graphiques
# -------------------------------------------------------------------
with onglet_vue:
    st.title("Sécurité routière à Paris — Vue d'ensemble")

    nb_accidents = df_filtre["Num_Acc"].nunique()
    nb_tues = int((df_filtre["grav"] == 2).sum())
    nb_hospitalises = int((df_filtre["grav"] == 3).sum())
    taux_gravite = (
        round(100 * (nb_tues + nb_hospitalises) / len(df_filtre), 2)
        if len(df_filtre) > 0
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accidents", f"{nb_accidents:,}")
    c2.metric("Tués", f"{nb_tues:,}")
    c3.metric("Blessés hospitalisés", f"{nb_hospitalises:,}")
    c4.metric("Taux de gravité", f"{taux_gravite} %")

    st.subheader("Évolution par année")
    if not df_filtre.empty:
        par_annee = df_filtre.groupby("annee")["Num_Acc"].nunique()
        st.bar_chart(par_annee)

    st.subheader("Répartition par mois")
    if not df_filtre.empty and "mois" in df_filtre.columns:
        par_mois = df_filtre.groupby("mois")["Num_Acc"].nunique()
        st.bar_chart(par_mois)

# -------------------------------------------------------------------
# ONGLET 2 — Carte
# -------------------------------------------------------------------
with onglet_carte:
    st.title("Carte des accidents")
    if not FOLIUM_DISPONIBLE:
        st.warning(
            "folium / streamlit-folium non installés. "
            "Lancez : pip install folium streamlit-folium"
        )
    else:
        df_geo = df_filtre.dropna(subset=["lat", "lon"])
        if df_geo.empty:
            st.info("Aucun accident géolocalisé pour ces filtres.")
        else:
            centre = [df_geo["lat"].mean(), df_geo["lon"].mean()]
            carte = folium.Map(location=centre, zoom_start=12)
            # Limite d'affichage pour ne pas surcharger le navigateur
            for _, row in df_geo.head(1000).iterrows():
                couleur = "red" if row["grav"] in (2, 3) else "blue"
                folium.CircleMarker(
                    location=[row["lat"], row["lon"]],
                    radius=3,
                    color=couleur,
                    fill=True,
                    fill_opacity=0.6,
                ).add_to(carte)
            st_folium(carte, width=1000, height=600)
            st.caption(
                f"{len(df_geo):,} accidents géolocalisés "
                f"(affichage limité aux 1000 premiers). Rouge = grave, bleu = léger/indemne."
            )

# -------------------------------------------------------------------
# ONGLET 3 — Limites connues (issues des tâches 37-49)
# -------------------------------------------------------------------
with onglet_limites:
    st.title("Limites connues du dataset")
    st.markdown(
        """
- **Capteur trafic (`iu_ac`)** : identifié pour 97,8 % des accidents (tâche 37),
  via matching exact puis proximité ~1 km.
- **Couverture trafic (`q_total`)** : seulement ~49 % des accidents ont une
  mesure de trafic pour la semaine exacte de l'accident (couverture temporelle
  des capteurs, tâche 38) — pas un bug, une vraie limite de données.
- **Population** : jointe au niveau commune (`com`), pas au niveau adresse
  exacte — donc un indicateur par zone, pas par point précis.
- **Corrélations météo/trafic × gravité (tâches 46-47)** : les tests du
  Khi-deux montrent des relations statistiquement présentes mais **faibles**
  (V de Cramér < 0,02) — la météo et le trafic seuls n'expliquent pas
  fortement la gravité d'un accident.
- **Analyse spatiale (tâche 45)** : uniquement sur les 4 191 accidents avec
  coordonnées lat/lon valides (Num_Acc géolocalisés), pas sur l'ensemble
  du dataset.
        """
    )