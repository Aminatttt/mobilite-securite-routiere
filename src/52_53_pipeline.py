#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================
TÂCHES 52 + 53 — CIBLE BINAIRE + FEATURE ENGINEERING
============================================================

Objectif :
  52. Définir la cible binaire 'grave' SANS fuite de données
  53. Feature engineering + split train/test + exports CSV

Entrées : data/mobilite_paris.db → FAIT_ACCIDENT_ENRICHI
Sorties : output/tache_52_53/*.csv

RÈGLE D'OR : la cible ne doit JAMAIS apparaître dans X
============================================================
"""

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

warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURATION
# ============================================================
DB_PATH = Path("data/mobilite_paris.db")
TABLE = "FAIT_ACCIDENT_ENRICHI"
OUT_DIR = Path("output/tache_52_53")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "grave"
SPLIT_ANNEE = 2023

# ------------------------------------------------------------
# COLONNES INTERDITES (FUITE DE DONNÉES)
# ------------------------------------------------------------
LEAKAGE_COLS = {
    "id_fait", "Num_Acc", "id_usager",
    "grav", "gravite", "catu", "categorie_usager",
    "secu1", "secu2", "secu3",
    "equipement_secu1", "equipement_secu2", "equipement_secu3",
    "type_collision",
    "date", "annee_semaine",
    "com", "population_annee",
}

# ------------------------------------------------------------
# FEATURES AUTORISÉES
# ------------------------------------------------------------
FEATURES_NUM_BRUTES = [
    "lat", "lon",
    "meteo_precipitations", "meteo_temp_min",
    "meteo_temp_max", "meteo_temp_moy",
    "q_moyen", "k_moyen",
    "population",
    "luminosite", "conditions_atmo",
    "categorie_vehicule",
]

FEATURES_CAT_BRUTES = [
    "arrondissement",
    "jour_semaine",
    "grain_trafic",
]


# ============================================================
# TÂCHE 52 — DÉFINIR LA CIBLE BINAIRE 'GRAVE'
# ============================================================
def definir_cible(df):
    print("\n" + "=" * 75)
    print("TÂCHE 52 — DÉFINITION DE LA CIBLE BINAIRE")
    print("=" * 75)

    if TARGET in df.columns:
        print(f"   Cible '{TARGET}' déjà présente dans la base")
    elif "grav" in df.columns:
        print(f"   → Création de '{TARGET}' depuis 'grav'")
        df[TARGET] = df["grav"].isin([2, 3]).astype(int)
        print(f"   Cible créée (grav ∈ {{2, 3}} → 1)")
    else:
        raise ValueError("Ni 'grave' ni 'grav' trouvés")

    counts = df[TARGET].value_counts().sort_index()
    pct = df[TARGET].value_counts(normalize=True).sort_index() * 100

    print(f"\n   Distribution de la cible :")
    for val in [0, 1]:
        n = counts.get(val, 0)
        p = pct.get(val, 0)
        label = "Non grave" if val == 0 else "GRAVE    "
        print(f"      {label} ({val}) : {n:>6,}  ({p:5.1f}%)")

    ratio = counts.get(1, 0) / max(counts.get(0, 1), 1)
    print(f"\n   Ratio minoritaire/majoritaire : 1:{1/ratio:.1f}")

    if ratio < 0.2:
        print("   DÉSÉQUILIBRE IMPORTANT détecté")
        print("      → à traiter en tâche 57")
    elif ratio < 0.4:
        print("   Déséquilibre modéré")
    else:
        print("   Classes relativement équilibrées")

    print(f"\n   Vérification anti-fuite :")
    if TARGET in LEAKAGE_COLS:
        raise ValueError(f"La cible '{TARGET}' est dans LEAKAGE_COLS")

    suspects = [c for c in df.columns
                if c != TARGET and any(k in c.lower()
                                       for k in ["grav", "catu", "secu"])]
    if suspects:
        print(f"      Colonnes suspectes (exclues auto) :")
        for c in suspects:
            print(f"         • {c}")

    return df


# ============================================================
# TÂCHE 53 — FEATURE ENGINEERING
# ============================================================
def feature_engineering(df):
    print("\n" + "=" * 75)
    print("TÂCHE 53 — FEATURE ENGINEERING")
    print("=" * 75)

    initial = len(df.columns)

    # Date décomposée
    if "AAAAMMJJ" in df.columns:
        s = pd.to_numeric(df["AAAAMMJJ"], errors="coerce").round().astype("Int64")
        dt = pd.to_datetime(s.astype(str), format="%Y%m%d", errors="coerce")

        df["annee"] = dt.dt.year
        df["mois"] = dt.dt.month
        df["jour"] = dt.dt.day
        df["jour_semaine_num"] = dt.dt.dayofweek
        df["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
        df["semaine_annee"] = dt.dt.isocalendar().week.astype("Int64")
        df["trimestre"] = dt.dt.quarter

        n_nat = int(dt.isna().sum())
        annees_ok = sorted(df["annee"].dropna().unique().tolist())
        print(f"   Parsing dates : {n_nat} NaT, années = {annees_ok}")

        df["saison"] = df["mois"].map({
            12: "hiver", 1: "hiver", 2: "hiver",
            3: "printemps", 4: "printemps", 5: "printemps",
            6: "ete", 7: "ete", 8: "ete",
            9: "automne", 10: "automne", 11: "automne"
        })

        feries = {"01-01", "05-01", "05-08", "07-14",
                  "08-15", "11-01", "11-11", "12-25"}
        df["jour_mois"] = dt.dt.strftime("%m-%d")
        df["is_ferie"] = df["jour_mois"].isin(feries).astype(int)

    # Météo dérivée
    if "meteo_precipitations" in df.columns:
        df["meteo_precipitations"] = pd.to_numeric(
            df["meteo_precipitations"], errors="coerce")
        df["is_pluie"] = (df["meteo_precipitations"] > 1).astype(int)

    # Trafic dérivé
    if "q_moyen" in df.columns and "k_moyen" in df.columns:
        df["q_moyen"] = pd.to_numeric(df["q_moyen"], errors="coerce")
        df["k_moyen"] = pd.to_numeric(df["k_moyen"], errors="coerce")
        df["ratio_saturation"] = df["k_moyen"] / (df["q_moyen"] + 1)
        median_q = df["q_moyen"].median()
        df["trafic_eleve"] = (df["q_moyen"] > median_q).astype(int)

    # Population
    if "population" in df.columns:
        df["population"] = pd.to_numeric(df["population"], errors="coerce")

    print(f"   → {len(df.columns) - initial} nouvelles features créées")
    return df


def selectionner_features(df):
    print("\nSélection des features ...")

    autorisees = set(FEATURES_NUM_BRUTES + FEATURES_CAT_BRUTES)
    autorisees |= {
        "annee", "mois", "jour", "jour_semaine_num", "is_weekend",
        "semaine_annee", "trimestre", "saison", "is_ferie",
        "is_pluie", "ratio_saturation", "trafic_eleve"
    }
    autorisees -= LEAKAGE_COLS

    features = [c for c in autorisees if c in df.columns]

    for c in features:
        if any(k in c.lower() for k in ["grav", "catu", "secu", "target"]):
            print(f"   Retrait de '{c}' (fuite potentielle)")
            features.remove(c)

    print(f"   → {len(features)} features retenues :")
    for c in sorted(features):
        print(f"      • {c}")

    return features


def nettoyer_features(df, features):
    print("\nNettoyage ...")
    X = df[features].copy()

    for c in X.columns:
        n_na = X[c].isna().sum()
        if n_na == 0:
            continue
        pct = n_na * 100 / len(X)

        if X[c].dtype == "object" or X[c].dtype.name == "category":
            mode = X[c].mode()[0] if not X[c].mode().empty else "INCONNU"
            X[c] = X[c].fillna(mode)
            print(f"   • {c:<25} : {n_na:>5} NA ({pct:4.1f}%) → mode '{mode}'")
        else:
            median = X[c].median()
            X[c] = X[c].fillna(median)
            print(f"   • {c:<25} : {n_na:>5} NA ({pct:4.1f}%) → médiane {median:.2f}")

    print(f"   → NA restants : {X.isna().sum().sum()}")
    return X


def encoder_categorielles(X):
    print("\nEncodage catégoriel ...")
    cat_cols = X.select_dtypes(
        include=["object", "category"]
    ).columns.tolist()

    if not cat_cols:
        print("   → Aucune variable catégorielle")
        return X

    for c in cat_cols:
        n = X[c].nunique()
        print(f"   • {c:<25} : {n} modalités")

        if n > 20:
            top = X[c].value_counts().nlargest(20).index
            X[c] = X[c].where(X[c].isin(top), "AUTRE")
            print(f"     > 20 modalités → regroupées en 'AUTRE'")

    X = pd.get_dummies(
        X,
        columns=cat_cols,
        drop_first=True,
        dtype=int
    )

    print(f"   → shape final : {X.shape}")
    return X


# ============================================================
# SPLIT TRAIN/TEST
# ============================================================
def split_temporel(df, X, y):
    print(f"\nSplit train/test (temporel, comme validé en tâche 54) ...")

    # Découpage par JOUR (AAAAMMJJ), pas par année : c'est ce que la tâche 54
    # a validé (pivot au jour 20241019, aucun accident coupé). Le découpage
    # par 'annee' ne fonctionne pas ici car tout le dataset est sur 2024.
    if "AAAAMMJJ" not in df.columns:
        raise ValueError(
            "'AAAAMMJJ' absent : impossible de faire le split temporel "
            "recommandé par la tâche 54."
        )

    jours = pd.to_numeric(df["AAAAMMJJ"], errors="coerce")
    jours_uniques = np.sort(jours.dropna().unique())
    idx_pivot = int(len(jours_uniques) * 0.80)
    date_pivot = jours_uniques[idx_pivot]

    mask_train = jours < date_pivot
    mask_test = jours >= date_pivot

    X_train, y_train = X[mask_train], y[mask_train]
    X_test, y_test = X[mask_test], y[mask_test]

    total = len(X_train) + len(X_test)
    if total == 0:
        raise ValueError("Split vide !")

    print(f"   Date pivot (début Test) : {int(date_pivot)}")
    print(f"   Train : {len(X_train):,} lignes ({len(X_train)/total*100:.1f}%)")
    print(f"   Test  : {len(X_test):,} lignes ({len(X_test)/total*100:.1f}%)")
    print(f"\n   Taux grave (train) : {y_train.mean()*100:.1f}%")
    print(f"   Taux grave (test)  : {y_test.mean()*100:.1f}%")

    return X_train, X_test, y_train, y_test

    # Split temporel classique
    mask_train = df["annee"] < SPLIT_ANNEE
    mask_test = df["annee"] == SPLIT_ANNEE

    X_train, y_train = X[mask_train], y[mask_train]
    X_test, y_test = X[mask_test], y[mask_test]

    total = len(X_train) + len(X_test)

    if total == 0:
        raise ValueError("Split vide !")

    print(
        f"   Train : {len(X_train):,} lignes "
        f"({len(X_train)/total*100:.1f}%)"
    )
    print(
        f"   Test  : {len(X_test):,} lignes "
        f"({len(X_test)/total*100:.1f}%)"
    )

    print(f"\n   Taux grave (train) : {y_train.mean()*100:.1f}%")
    print(f"   Taux grave (test)  : {y_test.mean()*100:.1f}%")

    return X_train, X_test, y_train, y_test


def calcul_vif(X):
    print("\nVIF ...")

    try:
        from statsmodels.stats.outliers_influence import (
            variance_inflation_factor
        )
    except ImportError:
        print("   statsmodels non installé")
        return None

    X_num = X.select_dtypes(include=[np.number]).dropna()
    X_num = X_num.loc[:, X_num.nunique() > 1]

    if X_num.shape[1] < 2:
        return None

    vif = pd.DataFrame({
        "Variable": X_num.columns,
        "VIF": [
            variance_inflation_factor(X_num.values, i)
            for i in range(X_num.shape[1])
        ]
    }).sort_values("VIF", ascending=False)

    return vif


def rapport_qualite(X_train, X_test):
    rows = []

    for col in X_train.columns:
        rows.append({
            "feature": col,
            "dtype": str(X_train[col].dtype),
            "n_unique_train": X_train[col].nunique(),
            "n_unique_test": (
                X_test[col].nunique()
                if col in X_test.columns
                else 0
            ),
            "mean_train": (
                X_train[col].mean()
                if X_train[col].dtype != "object"
                else None
            ),
            "std_train": (
                X_train[col].std()
                if X_train[col].dtype != "object"
                else None
            ),
            "pct_na_train": X_train[col].isna().mean() * 100,
            "pct_na_test": (
                X_test[col].isna().mean() * 100
                if col in X_test.columns
                else None
            ),
        })

    return pd.DataFrame(rows)


# ============================================================
# VISUALISATIONS
# ============================================================
def plot_distribution(y_train, y_test):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    for ax, y, name in zip(
        axes,
        [y_train, y_test],
        ["Train", "Test"]
    ):
        c = y.value_counts().sort_index()
        colors = ["#2ca02c", "#d62728"]

        ax.bar(
            ["Non grave (0)", "Grave (1)"],
            c.values,
            color=colors
        )

        ax.set_title(
            f"Distribution cible — {name}",
            fontweight="bold"
        )

        for i, v in enumerate(c.values):
            ax.text(
                i,
                v,
                f"{v}\n({v/len(y)*100:.1f}%)",
                ha="center",
                va="bottom"
            )

    plt.tight_layout()

    p = OUT_DIR / "distribution_cible.png"
    plt.savefig(p, dpi=140, bbox_inches="tight")
    plt.close()

    print(f"   {p}")


def plot_feature_importance(X_train, y_train, top_n=20):
    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        return None

    print("\nFeature importance (Random Forest) ...")

    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1
    )

    rf.fit(X_train, y_train)

    imp = pd.DataFrame({
        "feature": X_train.columns,
        "importance": rf.feature_importances_
    }).sort_values(
        "importance",
        ascending=False
    ).head(top_n)

    fig, ax = plt.subplots(figsize=(10, 7))

    ax.barh(
        imp["feature"][::-1],
        imp["importance"][::-1],
        color="#1f77b4"
    )

    ax.set_xlabel("Importance")
    ax.set_title(
        f"Top {top_n} features (Random Forest)",
        fontweight="bold"
    )

    plt.tight_layout()

    p = OUT_DIR / "feature_importances.png"
    plt.savefig(p, dpi=140, bbox_inches="tight")
    plt.close()

    print(f"   {p}")

    return imp


def plot_vif(vif, filename="vif.png"):
    if vif is None or len(vif) == 0:
        return

    top = vif.head(20)

    fig, ax = plt.subplots(figsize=(10, 7))

    colors = [
        "#d62728" if v >= 10
        else "#ff7f0e" if v >= 5
        else "#2ca02c"
        for v in top["VIF"]
    ]

    ax.barh(
        top["Variable"][::-1],
        top["VIF"][::-1],
        color=colors[::-1]
    )

    ax.axvline(
        5,
        color="orange",
        linestyle="--",
        alpha=.5,
        label="5 (modéré)"
    )

    ax.axvline(
        10,
        color="red",
        linestyle="--",
        alpha=.5,
        label="10 (fort)"
    )

    ax.set_xlabel("VIF")
    ax.set_title(
        "Multicolinéarité (top 20)",
        fontweight="bold"
    )

    ax.legend()

    plt.tight_layout()

    p = OUT_DIR / filename
    plt.savefig(p, dpi=140, bbox_inches="tight")
    plt.close()

    print(f"   {p}")


# ============================================================
# RAPPORT TEXTE
# ============================================================
def ecrire_rapport(X_train, X_test, y_train, y_test, vif, imp, df):
    path = OUT_DIR / "rapport_tache_52_53.txt"

    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 75 + "\n")
        f.write("RAPPORT TÂCHES 52 + 53 — CIBLE + FEATURES\n")
        f.write(
            f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write(f"Source : {DB_PATH} / {TABLE}\n")
        f.write(f"Échantillon total : {len(df):,} lignes\n")
        f.write("=" * 75 + "\n\n")

        f.write("TÂCHE 52 — CIBLE BINAIRE 'GRAVE'\n")
        f.write("-" * 75 + "\n")
        f.write(
            "  Règle : grave = 1 si grav ∈ "
            "{2 (tué), 3 (blessé hosp.)}\n"
        )
        f.write(f"  Total lignes : {len(df):,}\n")
        f.write(
            f"  Cas graves   : {df[TARGET].sum():,} "
            f"({df[TARGET].mean()*100:.1f}%)\n"
        )
        f.write(
            f"  Cas légers   : {(1-df[TARGET]).sum():,} "
            f"({(1-df[TARGET].mean())*100:.1f}%)\n"
        )

        ratio = df[TARGET].mean() / (1 - df[TARGET].mean())

        f.write(f"  Ratio        : 1:{1/ratio:.1f}\n")

        if ratio < 0.2:
            f.write(
                "  Déséquilibre important "
                "→ à traiter en tâche 57\n"
            )

        f.write("\n")

        f.write("TÂCHE 53 — FEATURES\n")
        f.write("-" * 75 + "\n")
        f.write(f"  Features finales : {X_train.shape[1]}\n")
        f.write(f"  Train : {X_train.shape[0]:,} lignes\n")
        f.write(f"  Test  : {X_test.shape[0]:,} lignes\n")
        f.write(
            f"  Taux grave (train) : "
            f"{y_train.mean()*100:.1f}%\n"
        )
        f.write(
            f"  Taux grave (test)  : "
            f"{y_test.mean()*100:.1f}%\n\n"
        )

        f.write("COLONNES EXCLUES (anti-fuite) :\n")

        for c in sorted(LEAKAGE_COLS):
            f.write(f"  {c}\n")

        f.write(
            f"\nFEATURES RETENUES ({X_train.shape[1]}) :\n"
        )

        for c in X_train.columns:
            f.write(f"  • {c}\n")

        if vif is not None:
            f.write("\nVIF (top 15) :\n")

            for _, r in vif.head(15).iterrows():
                v = r["VIF"]

                if v >= 10:
                    niveau = "fort"
                elif v >= 5:
                    niveau = "modéré"
                else:
                    niveau = "faible"

                f.write(
                    f"  {r['Variable']:<30} : "
                    f"{v:7.2f}  {niveau}\n"
                )

        if imp is not None:
            f.write(
                "\nTOP FEATURES (Random Forest) :\n"
            )

            for _, r in imp.head(15).iterrows():
                f.write(
                    f"  {r['feature']:<30} : "
                    f"{r['importance']:.4f}\n"
                )

        f.write("\nNOTES\n")
        f.write("-" * 75 + "\n")
        f.write(
            "  Split aléatoire stratifié (une seule année)\n"
        )
        f.write(
            "  La cible 'grave' est ABSENTE de X\n"
        )
        f.write(
            "  Vérifier périodiquement les nouvelles colonnes\n"
        )

    print(f"   {path}")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 75)
    print("TÂCHES 52 + 53 — CIBLE + FEATURE ENGINEERING")
    print("=" * 75)

    # 1. Chargement
    print(f"\nChargement de {DB_PATH} / {TABLE} ...")

    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        f'SELECT * FROM "{TABLE}";',
        conn
    )

    conn.close()

    print(
        f"   → {len(df):,} lignes × "
        f"{len(df.columns)} colonnes"
    )

    # 2. Tâche 52 — Cible
    df = definir_cible(df)

    # 3. Tâche 53 — Feature engineering
    df = feature_engineering(df)

    # 4. Sélection
    features = selectionner_features(df)

    # 5. Nettoyage
    X = nettoyer_features(df, features)
    y = df[TARGET].astype(int)

    # 6. Encodage
    X = encoder_categorielles(X)

    # 7. Split
    X_train, X_test, y_train, y_test = split_temporel(
        df,
        X,
        y
    )

    # 8. VIF
    vif = calcul_vif(X_train)

    if vif is not None:
        vif.to_csv(
            OUT_DIR / "vif_report.csv",
            index=False
        )

    # 9. Qualité
    q = rapport_qualite(X_train, X_test)

    q.to_csv(
        OUT_DIR / "rapport_qualite.csv",
        index=False
    )

    # 10. Visualisations
    print("\nVisualisations ...")

    plot_distribution(
        y_train,
        y_test
    )

    if vif is not None:
        plot_vif(vif)

    imp = plot_feature_importance(
        X_train,
        y_train
    )

    # 11. Exports CSV
    print("\nExports CSV ...")

    X_train_export = X_train.copy()
    X_test_export = X_test.copy()

    for c in X_train_export.columns:

        if str(X_train_export[c].dtype) == "Int64":
            X_train_export[c] = (
                X_train_export[c].astype("int32")
            )

        if str(X_test_export[c].dtype) == "Int64":
            X_test_export[c] = (
                X_test_export[c].astype("int32")
            )

    X_train_export.to_csv(
        OUT_DIR / "features_train.csv",
        index=False
    )

    X_test_export.to_csv(
        OUT_DIR / "features_test.csv",
        index=False
    )

    y_train.to_frame(TARGET).to_csv(
        OUT_DIR / "y_train.csv",
        index=False
    )

    y_test.to_frame(TARGET).to_csv(
        OUT_DIR / "y_test.csv",
        index=False
    )

    print(
        f"   4 fichiers CSV dans {OUT_DIR}/"
    )

    # Dictionnaire
    dico = pd.DataFrame({
        "feature": list(X_train.columns),
        "type": [
            str(X_train[c].dtype)
            for c in X_train.columns
        ],
    })

    dico.to_csv(
        OUT_DIR / "feature_dictionary.csv",
        index=False
    )

    print("   feature_dictionary.csv")

    # 12. Rapport
    print("\nRapport ...")

    ecrire_rapport(
        X_train,
        X_test,
        y_train,
        y_test,
        vif,
        imp,
        df
    )

    # 13. Résumé console
    print("\n" + "=" * 75)
    print("RÉSUMÉ FINAL")
    print("=" * 75)

    print(f"  Cible            : '{TARGET}'")
    print(f"  Total lignes     : {len(df):,}")
    print(
        f"  Cas graves      : "
        f"{df[TARGET].sum():,} "
        f"({df[TARGET].mean()*100:.1f}%)"
    )
    print(f"  Features         : {X_train.shape[1]}")
    print(f"  Train            : {X_train.shape[0]:,} lignes")
    print(f"  Test             : {X_test.shape[0]:,} lignes")

    if vif is not None:
        n_fort = (vif["VIF"] >= 10).sum()
        n_mod = (
            (vif["VIF"] >= 5)
            & (vif["VIF"] < 10)
        ).sum()

        print(f"\n  VIF ≥ 10 (à retirer) : {n_fort}")
        print(f"  VIF 5-10 (modéré)    : {n_mod}")

    print("\n" + "=" * 75)
    print(
        f"Tâches 52 + 53 terminées — "
        f"résultats dans {OUT_DIR}/"
    )
    print("=" * 75)

    print(
        "\n→ Prochaine étape : "
        "tâche 55 (baseline) avec les CSV"
    )


if __name__ == "__main__":
    main()