"""
Tache 43 - Evolution pluriannuelle des accidents a Paris (2020-2023).
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# --- CHEMINS ---
RACINE = Path(__file__).resolve().parent.parent
CURATED = RACINE / "data" / "curated"
RAW = RACINE / "data" / "raw" / "baac"
RESULTATS = CURATED / "resultats" / "tache_43"
RESULTATS.mkdir(parents=True, exist_ok=True)

ANNEES = [2020, 2021, 2022, 2023]

# --- DOSSIER SOURCE ---
DOSSIER = sorted([d for d in RAW.iterdir() if d.is_dir()])[-1]
print(f"Source : {DOSSIER.name}")

# --- CHARGEMENT ---
frames = []
for annee in ANNEES:
    fichiers = list(DOSSIER.glob(f"*{annee}.csv"))

    # Separer caracteristiques et usagers
    f_caract = [f for f in fichiers if "usager" not in f.name][0]
    f_usagers = [f for f in fichiers if "usager" in f.name][0]

    # Lecture
    df_c = pd.read_csv(f_caract, sep=";", encoding="utf-8-sig", low_memory=False)
    df_u = pd.read_csv(f_usagers, sep=";", encoding="utf-8-sig", low_memory=False)

    # 2022 : renommer Accident_Id -> Num_Acc
    df_c = df_c.rename(columns={"Accident_Id": "Num_Acc"})

    # 🔧 Filtrage Paris - CORRIGE : convertir en int d'abord
    df_c["dep"] = pd.to_numeric(df_c["dep"], errors="coerce")
    df_c = df_c[df_c["dep"] == 75]

    # Jointure
    df = df_u.merge(df_c, on="Num_Acc", how="inner")
    df["annee"] = annee
    frames.append(df)
    print(f"  {annee} : {len(df)} lignes")

df = pd.concat(frames, ignore_index=True)
print(f"\nTotal : {len(df)} lignes")
print(f"Annees : {sorted(df['annee'].unique())}")
print(f"Distribution grav :\n{df['grav'].value_counts().sort_index().to_string()}")

# Sauvegarde consolidee
(CURATED / "baac").mkdir(parents=True, exist_ok=True)
df.to_csv(CURATED / "baac" / "accidents_paris_2020_2023.csv",
          sep=";", index=False, encoding="utf-8")

# --- AGREGATION PAR ANNEE ---
df["grav"] = pd.to_numeric(df["grav"], errors="coerce")
df = df[df["grav"].isin([1, 2, 3, 4])]

# Gravite max par accident : 2 (tue) > 3 (hosp) > 4 (leger) > 1 (indemne)
# Poids : 1=indemne(0), 2=tue(3), 3=hosp(2), 4=leger(1)
poids = {1: 0, 2: 3, 3: 2, 4: 1}
df["poids"] = df["grav"].map(poids)
idx = df.groupby(["annee", "Num_Acc"])["poids"].idxmax()
acc = df.loc[idx]

# Tableau final
tableau = acc.groupby("annee").apply(lambda g: pd.Series({
    "nb_accidents": len(g),
    "nb_tues": int((g["grav"] == 2).sum()),
    "nb_blesses_hospitalises": int((g["grav"] == 3).sum()),
    "nb_blesses_legers": int((g["grav"] == 4).sum()),
    "taux_gravite_pct": round(100 * ((g["grav"] == 2) | (g["grav"] == 3)).sum() / len(g), 2),
})).reset_index()

print("\n", tableau.to_string(index=False))
tableau.to_csv(RESULTATS / "evolution_2020_2023.csv",
               sep=";", index=False, encoding="utf-8")

# --- GRAPHIQUE ---
fig, ax = plt.subplots(1, 2, figsize=(14, 5))

ax[0].bar(tableau["annee"].astype(str), tableau["nb_accidents"], color="steelblue")
ax[0].set_title("Accidents par an (Paris)")
ax[0].set_ylabel("Nb accidents")

ax[1].bar(tableau["annee"].astype(str), tableau["nb_tues"], label="Tues", color="black")
ax[1].bar(tableau["annee"].astype(str), tableau["nb_blesses_hospitalises"],
          bottom=tableau["nb_tues"], label="Blesses hosp.", color="red")
ax[1].bar(tableau["annee"].astype(str), tableau["nb_blesses_legers"],
          bottom=tableau["nb_tues"] + tableau["nb_blesses_hospitalises"],
          label="Blesses legers", color="orange")
ax[1].set_title("Gravite par an")
ax[1].legend()

plt.tight_layout()
plt.savefig(RESULTATS / "evolution_2020_2023.png", dpi=120)
plt.close()

print(f"\nOK - resultats dans {RESULTATS}")