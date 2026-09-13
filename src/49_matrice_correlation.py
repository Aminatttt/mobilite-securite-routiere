#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
TÂCHE 49 — MATRICE DE CORRÉLATIONS / RELATIONS ENTRE VARIABLES
============================================================

Entrées : data/mobilite_paris.db  ->  table FAIT_ACCIDENT_ENRICHI
Sorties : output/tache_49/*

Analyses réalisées :
  1. Matrice de Pearson        (relations linéaires)
  2. Matrice de Spearman       (relations monotones, robuste)
  3. Matrice de Cramér's V     (relations catégorielles)
  4. Tests de significativité  (p-values + étoiles)
  5. Top corrélations          (avec la gravité)
  6. VIF                       (multicolinéarité)
  7. Information Mutuelle      (relations non linéaires)
  8. Export Phase 5            (variables à retenir)
============================================================
"""

import os
import sys
import sqlite3
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency, pearsonr, spearmanr

warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURATION
# ============================================================
DB_PATH = Path("data/mobilite_paris.db")
OUT_DIR = Path("output/tache_49")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TABLE = "FAIT_ACCIDENT_ENRICHI"
TARGET = "gravite"

NUM_COLS = [
    "lat", "lon",
    "q_total", "q_moyen", "k_moyen",
    "meteo_precipitations", "meteo_temp_min", "meteo_temp_max",
    "population",
    "luminosite", "conditions_atmo", "type_collision",
    "categorie_usager", "gravite",
    "equipement_secu1", "equipement_secu2",
    "categorie_vehicule",
]

CAT_COLS = [
    "arrondissement", "jour_semaine", "is_weekend",
    "annee", "mois", "annee_semaine", "grain_trafic",
]

SEUIL_FORT = 0.5
SEUIL_MOYEN = 0.3
SEUIL_PHASE5 = 0.15
ALPHA = 0.05


# ============================================================
# 1. CHARGEMENT & PRÉPARATION
# ============================================================
def load_data():
    print(f"Chargement de {DB_PATH} / {TABLE} ...")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(f'SELECT * FROM "{TABLE}";', conn)
    conn.close()
    print(f"   -> {len(df):,} lignes x {len(df.columns)} colonnes")

    # Conversion numérique
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Ne supprimer QUE les colonnes 100% vides
    cols_ok = df.columns[df.notna().any()]
    cols_supprimees = set(df.columns) - set(cols_ok)
    if cols_supprimees:
        print(f"   [INFO] Colonnes 100% vides supprimées : {cols_supprimees}")
    df = df[cols_ok]

    return df


def select_numeric(df):
    """Sélectionne les colonnes numériques exploitables"""
    cols = [c for c in NUM_COLS if c in df.columns]
    sub = df[cols].copy()
    sub = sub.dropna(axis=1, how="all")  # retire colonnes vides
    sub = sub.loc[:, sub.nunique() > 1]  # retire colonnes constantes
    return sub


# ============================================================
# 2. MATRICES DE CORRÉLATION
# ============================================================
def matrice_pearson(df):
    print("\nMatrice de Pearson ...")
    return df.corr(method="pearson")


def matrice_spearman(df):
    print("Matrice de Spearman ...")
    return df.corr(method="spearman")


def cramers_v(x, y):
    """V de Cramér entre 2 variables catégorielles"""
    confusion = pd.crosstab(x, y)
    if confusion.size == 0 or min(confusion.shape) < 2:
        return np.nan
    chi2 = chi2_contingency(confusion, correction=False)[0]
    n = confusion.sum().sum()
    phi2 = chi2 / n
    r, k = confusion.shape
    phi2corr = max(0, phi2 - ((k - 1) * (r - 1)) / (n - 1)) if n > 1 else 0
    rcorr = r - ((r - 1) ** 2) / (n - 1) if n > 1 else r
    kcorr = k - ((k - 1) ** 2) / (n - 1) if n > 1 else k
    denom = min(kcorr - 1, rcorr - 1)
    return np.sqrt(phi2corr / denom) if denom > 0 else np.nan


def matrice_cramersv(df, cat_cols, max_card=50):
    print("Matrice de Cramér's V (catégorielles) ...")
    cols = [c for c in cat_cols if c in df.columns]
    cols = [c for c in cols if df[c].nunique() <= max_card]
    if len(cols) < 2:
        return None

    n = len(cols)
    mat = pd.DataFrame(np.eye(n), index=cols, columns=cols)
    for i in range(n):
        for j in range(i + 1, n):
            v = cramers_v(df[cols[i]], df[cols[j]])
            mat.iloc[i, j] = v
            mat.iloc[j, i] = v
    return mat


# ============================================================
# 3. TOP CORRÉLATIONS & SIGNIFICATIVITÉ
# ============================================================
def top_correlations(corr_matrix, top_n=25):
    """Extrait les paires les plus corrélées (hors diagonale)"""
    mat = corr_matrix.where(~np.eye(len(corr_matrix), dtype=bool))
    pairs = (
        mat.stack()
        .reset_index()
        .rename(columns={"level_0": "var1", "level_1": "var2", 0: "correlation"})
    )
    pairs["key"] = pairs.apply(lambda r: tuple(sorted([r["var1"], r["var2"]])), axis=1)
    pairs = pairs.drop_duplicates("key").drop(columns="key")
    pairs["abs_corr"] = pairs["correlation"].abs()
    pairs = pairs.sort_values("abs_corr", ascending=False).head(top_n)
    pairs["force"] = pairs["abs_corr"].apply(
        lambda x: "FORTE" if x >= SEUIL_FORT
        else "MOYENNE" if x >= SEUIL_MOYEN
        else "FAIBLE"
    )
    pairs["sens"] = np.where(pairs["correlation"] > 0, "positive (+)", "negative (-)")
    return pairs.reset_index(drop=True)


def tests_significativite(df, top_pairs):
    """Pearson + Spearman + p-value sur les paires du top"""
    results = []
    for _, row in top_pairs.iterrows():
        a, b = row["var1"], row["var2"]
        try:
            r_p, p_p = pearsonr(df[a], df[b])
            r_s, p_s = spearmanr(df[a], df[b])
            results.append({
                "var1": a, "var2": b,
                "pearson_r": r_p, "pearson_p": p_p,
                "spearman_r": r_s, "spearman_p": p_s,
                "significatif": "OUI" if p_p < ALPHA else "NON",
                "etoiles": ("***" if p_p < 0.001 else "**" if p_p < 0.01
                            else "*" if p_p < 0.05 else "ns")
            })
        except Exception:
            continue
    return pd.DataFrame(results)


# ============================================================
# 4. TOP CORRÉLATIONS AVEC LA GRAVITÉ
# ============================================================
def top_avec_cible(spearman, target=TARGET, top_n=10):
    if target not in spearman.columns:
        return None
    corr_target = (
        spearman[target]
        .drop(target)
        .sort_values(key=abs, ascending=False)
    )
    return corr_target.head(top_n)


# ============================================================
# 5. VIF (Multicolinéarité)
# ============================================================
def calcul_vif(df):
    """Calcule le VIF pour détecter la multicolinéarité"""
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
    except ImportError:
        print("   [INFO] statsmodels non installé - VIF ignoré (pip install statsmodels)")
        return None

    df_vif = df.dropna().copy()
    df_vif = df_vif.loc[:, df_vif.nunique() > 1]
    if df_vif.shape[1] < 2:
        return None

    vif_data = pd.DataFrame()
    vif_data["Variable"] = df_vif.columns
    vif_data["VIF"] = [
        variance_inflation_factor(df_vif.values, i)
        for i in range(df_vif.shape[1])
    ]
    return vif_data.sort_values("VIF", ascending=False)


# ============================================================
# 6. INFORMATION MUTUELLE (relations non linéaires)
# ============================================================
def information_mutuelle(df, target=TARGET):
    if target not in df.columns:
        return None
    try:
        from sklearn.feature_selection import mutual_info_classif
    except ImportError:
        print("   [INFO] scikit-learn non installé - MI ignorée (pip install scikit-learn)")
        return None

    X = df.drop(columns=[target]).fillna(0)
    y = (df[target] > 0).astype(int)

    mi = mutual_info_classif(X, y, random_state=42)
    return pd.Series(mi, index=X.columns).sort_values(ascending=False)


# ============================================================
# 7. VISUALISATIONS
# ============================================================
def plot_heatmap(corr, title, filename, cmap="coolwarm", annot=True):
    fig, ax = plt.subplots(figsize=(14, 12))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, mask=mask, annot=annot, fmt=".2f", cmap=cmap,
        center=0, vmin=-1, vmax=1, square=True, linewidths=.5,
        cbar_kws={"shrink": .7}, ax=ax, annot_kws={"size": 8}
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    path = OUT_DIR / filename
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


def plot_heatmap_pvalues(corr, pvalues, filename="matrice_significativite.png"):
    """Heatmap avec les étoiles de significativité en annotation"""
    fig, ax = plt.subplots(figsize=(14, 12))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

    def annot(p):
        if pd.isna(p): return ""
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        return "ns"

    if hasattr(pvalues, "map"):
        annot_matrix = pvalues.map(annot)
    else:
        annot_matrix = pvalues.applymap(annot)

    sns.heatmap(
        corr, mask=mask, annot=annot_matrix, fmt="",
        cmap="coolwarm", center=0, vmin=-1, vmax=1,
        square=True, linewidths=.5, cbar_kws={"shrink": .7},
        ax=ax, annot_kws={"size": 8}
    )
    ax.set_title("Significativité (* p<0.05, ** p<0.01, *** p<0.001)",
                 fontsize=13, fontweight="bold", pad=15)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    path = OUT_DIR / filename
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


def plot_top_correlations(top_pairs, filename="top_correlations.png"):
    df = top_pairs.copy().head(15)
    df["label"] = df["var1"] + " - " + df["var2"]
    df = df.sort_values("correlation")

    colors = ["#d62728" if c < 0 else "#2ca02c" for c in df["correlation"]]

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.barh(df["label"], df["correlation"], color=colors, edgecolor="black")
    ax.axvline(0, color="black", linewidth=.8)
    ax.axvline(SEUIL_FORT, color="red", linestyle="--", alpha=.5,
               label=f"Seuil fort ({SEUIL_FORT})")
    ax.axvline(-SEUIL_FORT, color="red", linestyle="--", alpha=.5)
    ax.set_xlabel("Corrélation")
    ax.set_title("Top 15 des corrélations les plus fortes", fontweight="bold")
    ax.legend()
    plt.tight_layout()
    path = OUT_DIR / filename
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


def plot_top_gravite(corr_target, filename="top10_gravite.png"):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#d62728" if v > 0 else "#1f77b4" for v in corr_target.values]
    ax.barh(corr_target.index[::-1], corr_target.values[::-1], color=colors[::-1])
    ax.axvline(0, color="black", linewidth=.8)
    ax.set_xlabel("Coefficient de Spearman")
    ax.set_title(f"Top 10 variables corrélées à '{TARGET}'", fontweight="bold")
    ax.grid(axis="x", alpha=.3)
    plt.tight_layout()
    path = OUT_DIR / filename
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


def plot_mutual_info(mi_series, filename="mutual_info.png"):
    fig, ax = plt.subplots(figsize=(10, 6))
    top_mi = mi_series.head(10)
    ax.barh(top_mi.index[::-1], top_mi.values[::-1], color="#2ca02c")
    ax.set_xlabel("Information Mutuelle")
    ax.set_title("Top 10 Information Mutuelle avec la gravité", fontweight="bold")
    ax.grid(axis="x", alpha=.3)
    plt.tight_layout()
    path = OUT_DIR / filename
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


def plot_scatter_matrix_focus(df, top_pairs, filename="scatter_top3.png"):
    pairs = top_pairs.head(3)
    if len(pairs) == 0:
        return
    fig, axes = plt.subplots(1, len(pairs), figsize=(16, 5))
    if len(pairs) == 1:
        axes = [axes]
    for ax, (_, row) in zip(axes, pairs.iterrows()):
        a, b = row["var1"], row["var2"]
        ax.scatter(df[a], df[b], alpha=.3, s=8, color="#1f77b4")
        ax.set_xlabel(a)
        ax.set_ylabel(b)
        ax.set_title(f"{a} - {b}\nr = {row['correlation']:.3f}", fontsize=10)
        ax.grid(alpha=.3)
    plt.tight_layout()
    path = OUT_DIR / filename
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


def plot_pairplot(df, top_vars=None, filename="pairplot.png", max_cols=6):
    cols = top_vars if top_vars else list(df.columns[:max_cols])
    cols = [c for c in cols if c in df.columns][:max_cols]
    if len(cols) < 2:
        return
    g = sns.pairplot(
        df[cols].dropna().sample(min(2000, len(df)), random_state=42),
        diag_kind="kde", corner=True,
        plot_kws={"alpha": .4, "s": 10}
    )
    g.fig.suptitle("Pairplot des variables clés", y=1.02, fontweight="bold")
    path = OUT_DIR / filename
    g.savefig(path, dpi=110, bbox_inches="tight")
    plt.close()
    print(f"   -> {path}")


# ============================================================
# 8. MATRICE DE P-VALUES
# ============================================================
def matrice_pvalues(df):
    cols = df.columns
    pvals = pd.DataFrame(np.ones((len(cols), len(cols))),
                         columns=cols, index=cols)
    for i in cols:
        for j in cols:
            if i == j:
                pvals.loc[i, j] = 0.0
            else:
                try:
                    _, p = pearsonr(df[i], df[j])
                    pvals.loc[i, j] = p
                except Exception:
                    pvals.loc[i, j] = np.nan
    return pvals


# ============================================================
# 9. RAPPORT TEXTE COMPLET
# ============================================================
def ecrire_rapport(top_pairs, tests, cramersv, corr_target, vif, mi_series, n_rows):
    path = OUT_DIR / "rapport_tache49.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 75 + "\n")
        f.write("RAPPORT TÂCHE 49 — MATRICE DE CORRÉLATIONS\n")
        f.write(f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source : {DB_PATH} / {TABLE}\n")
        f.write(f"Échantillon : {n_rows:,} lignes\n")
        f.write("=" * 75 + "\n\n")

        # Top Pearson
        f.write("TOP 10 CORRÉLATIONS GLOBALES (Pearson)\n")
        f.write("-" * 75 + "\n")
        for _, r in top_pairs.head(10).iterrows():
            f.write(f"  {r['var1']:<25} - {r['var2']:<25}  "
                    f"r = {r['correlation']:+.3f}  {r['force']}  {r['sens']}\n")

        # Significativité
        f.write("\nTESTS DE SIGNIFICATIVITÉ (alpha = 0.05)\n")
        f.write("-" * 75 + "\n")
        for _, r in tests.head(10).iterrows():
            f.write(f"  {r['var1']:<20} - {r['var2']:<20}  "
                    f"r={r['pearson_r']:+.3f} (p={r['pearson_p']:.2e}) "
                    f"{r['etoiles']:<4}  {r['significatif']}\n")

        # Top gravité
        if corr_target is not None:
            f.write(f"\nTOP 10 CORRÉLATIONS AVEC '{TARGET.upper()}'\n")
            f.write("-" * 75 + "\n")
            for var, val in corr_target.items():
                force = ("très forte" if abs(val) >= 0.7 else
                         "forte"      if abs(val) >= 0.5 else
                         "modérée"    if abs(val) >= 0.3 else
                         "faible"     if abs(val) >= 0.15 else "très faible")
                f.write(f"  {var:<30} : {val:+.3f}  ({force})\n")

        # Cramér's V
        if cramersv is not None:
            f.write("\nTOP RELATIONS CATÉGORIELLES (Cramér's V)\n")
            f.write("-" * 75 + "\n")
            cv = cramersv.where(~np.eye(len(cramersv), dtype=bool)).stack() \
                .reset_index().rename(columns={"level_0": "v1", "level_1": "v2", 0: "V"})
            cv["key"] = cv.apply(lambda r: tuple(sorted([r["v1"], r["v2"]])), axis=1)
            cv = cv.drop_duplicates("key").sort_values("V", ascending=False).head(10)
            for _, r in cv.iterrows():
                f.write(f"  {r['v1']:<25} - {r['v2']:<25}  V = {r['V']:.3f}\n")

        # VIF
        if vif is not None:
            f.write("\nVIF (Multicolinéarité)\n")
            f.write("-" * 75 + "\n")
            f.write("  VIF < 5 -> OK | 5-10 -> modéré (ATTENTION) | >= 10 -> fort (PROBLEME)\n\n")
            for _, r in vif.head(10).iterrows():
                v = r["VIF"]
                icon = "PROBLEME" if v >= 10 else "ATTENTION" if v >= 5 else "OK"
                f.write(f"  {r['Variable']:<30} : {v:7.2f}  {icon}\n")

        # Information Mutuelle
        if mi_series is not None:
            f.write("\nINFORMATION MUTUELLE (top 10)\n")
            f.write("-" * 75 + "\n")
            for var, val in mi_series.head(10).items():
                f.write(f"  {var:<30} : {val:.4f}\n")

        # Interprétation
        f.write("\nINTERPRÉTATION\n")
        f.write("-" * 75 + "\n")
        f.write("  |r| >= 0.7  : très forte\n")
        f.write("  |r| >= 0.5  : forte\n")
        f.write("  |r| >= 0.3  : modérée\n")
        f.write("  |r| < 0.3  : faible\n\n")
        f.write("  ATTENTION : corrélation != causalité.\n")
        f.write("  ATTENTION : Cramér's V : 0 = aucune, 1 = parfaite\n")
        f.write("  ATTENTION : VIF >= 10 -> redondance problématique\n")

    print(f"   -> {path}")


# ============================================================
# 10. MAIN
# ============================================================
def main():
    print("=" * 75)
    print("TÂCHE 49 — MATRICE DE CORRÉLATIONS (VERSION FINALE)")
    print("=" * 75)

    # --- Chargement ---
    df = load_data()
    num_df = select_numeric(df)
    print(f"   -> {num_df.shape[1]} colonnes numériques retenues")

    if num_df.shape[1] < 2:
        print("[ERREUR] Pas assez de colonnes numériques pour analyser.")
        sys.exit(1)

    # --- Matrices ---
    pearson = matrice_pearson(num_df)
    spearman = matrice_spearman(num_df)
    cramersv = matrice_cramersv(df, CAT_COLS)
    pvalues = matrice_pvalues(num_df)

    # --- Top corrélations ---
    top = top_correlations(pearson, top_n=25)
    corr_target = top_avec_cible(spearman, TARGET, top_n=10)

    # --- Tests ---
    print("\nTests de significativité ...")
    tests = tests_significativite(num_df, top.head(15))

    # --- VIF ---
    print("\nCalcul du VIF ...")
    vif = calcul_vif(num_df)
    if vif is not None:
        vif.to_csv(OUT_DIR / "vif.csv", index=False)

    # --- Information Mutuelle ---
    print("\nInformation Mutuelle ...")
    mi_series = information_mutuelle(num_df, TARGET)
    if mi_series is not None:
        mi_series.to_csv(OUT_DIR / "mutual_info.csv", header=["mutual_info"])

    # --- Exports CSV ---
    print("\nExports CSV ...")
    pearson.to_csv(OUT_DIR / "matrice_pearson.csv")
    spearman.to_csv(OUT_DIR / "matrice_spearman.csv")
    if cramersv is not None:
        cramersv.to_csv(OUT_DIR / "matrice_cramersv.csv")
    pvalues.to_csv(OUT_DIR / "matrice_pvalues.csv")
    top.to_csv(OUT_DIR / "top_correlations.csv", index=False)
    tests.to_csv(OUT_DIR / "tests_significativite.csv", index=False)
    if corr_target is not None:
        corr_target.to_csv(OUT_DIR / "top10_gravite.csv", header=["correlation"])
    print(f"   -> fichiers CSV dans {OUT_DIR}/")

    # --- Export Phase 5 ---
    if corr_target is not None:
        vars_phase5 = corr_target[abs(corr_target) >= SEUIL_PHASE5].index.tolist()
        pd.DataFrame({"variable": vars_phase5}).to_csv(
            OUT_DIR / "variables_retenues_phase5.csv", index=False
        )
        print(f"   -> {len(vars_phase5)} variables retenues pour Phase 5 "
              f"(|corr| >= {SEUIL_PHASE5})")

    # --- Visualisations ---
    print("\nVisualisations ...")
    plot_heatmap(pearson, "Matrice de corrélation — Pearson", "matrice_pearson.png")
    plot_heatmap(spearman, "Matrice de corrélation — Spearman",
                 "matrice_spearman.png", cmap="vlag")
    if cramersv is not None:
        plot_heatmap(cramersv, "Matrice de Cramér's V — Variables catégorielles",
                     "matrice_cramersv.png", cmap="YlOrRd")
    plot_heatmap_pvalues(spearman, pvalues)
    plot_top_correlations(top)
    if corr_target is not None:
        plot_top_gravite(corr_target)
    if mi_series is not None:
        plot_mutual_info(mi_series)
    plot_scatter_matrix_focus(num_df, top)

    # Pairplot sur les variables les plus corrélées à la gravité
    if corr_target is not None:
        top_vars = corr_target.head(5).index.tolist() + [TARGET]
        plot_pairplot(num_df, top_vars=top_vars)
    else:
        plot_pairplot(num_df)

    # --- Rapport ---
    print("\nRapport ...")
    ecrire_rapport(top, tests, cramersv, corr_target, vif, mi_series, len(df))

    # --- Affichage console ---
    print("\n" + "=" * 75)
    print("TOP 10 CORRÉLATIONS GLOBALES (Pearson)")
    print("=" * 75)
    for _, r in top.head(10).iterrows():
        print(f"  {r['var1']:<22} - {r['var2']:<22}  "
              f"r = {r['correlation']:+.3f}  {r['force']}  {r['sens']}")

    if corr_target is not None:
        print("\n" + "=" * 75)
        print(f"TOP 10 CORRÉLATIONS AVEC '{TARGET.upper()}' (Spearman)")
        print("=" * 75)
        for var, val in corr_target.items():
            print(f"  {var:<30} : {val:+.3f}")

    if vif is not None:
        print("\n" + "=" * 75)
        print("VIF (top 5)")
        print("=" * 75)
        for _, r in vif.head(5).iterrows():
            v = r["VIF"]
            icon = "PROBLEME" if v >= 10 else "ATTENTION" if v >= 5 else "OK"
            print(f"  {r['Variable']:<30} : {v:7.2f}  {icon}")

    print("\n" + "=" * 75)
    print(f"Tâche 49 terminée — résultats dans {OUT_DIR}/")
    print("=" * 75)


if __name__ == "__main__":
    main()