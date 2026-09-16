"""
===============================================================================
TÂCHE 59 — EXPLICABILITÉ (feature importance / permutation / SHAP)
===============================================================================
Explique le modèle retenu (Gradient Boosting, seuil optimal validé en tâche 57)
avec 3 méthodes complémentaires :
  1. Feature importance native (déjà vue en tâche 56, rappelée ici pour repère)
  2. Permutation importance (plus fiable, mesurée directement sur le Test)
  3. SHAP (si disponible) : explique chaque prédiction individuellement

Entrées : output/tache_52_53/features_{train,test}.csv, y_{train,test}.csv
Sorties : output/tache_59/*
===============================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score

BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_5253 = BASE_DIR / "output" / "tache_52_53"
DOSSIER_SORTIE = BASE_DIR / "output" / "tache_59"
DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

TARGET = "grave"
SEUIL_OPTIMAL = 0.111  # validé en tâche 57


def charger_donnees():
    X_train = pd.read_csv(DOSSIER_5253 / "features_train.csv")
    X_test = pd.read_csv(DOSSIER_5253 / "features_test.csv")[X_train.columns]
    y_train = pd.read_csv(DOSSIER_5253 / "y_train.csv")[TARGET]
    y_test = pd.read_csv(DOSSIER_5253 / "y_test.csv")[TARGET]
    return X_train, X_test, y_train, y_test


def entrainer_modele(X_train, y_train):
    """Même configuration que la tâche 56/57 (Gradient Boosting)."""
    params = dict(n_estimators=300, learning_rate=0.05, subsample=0.8, random_state=42)
    try:
        from xgboost import XGBClassifier
        modele = XGBClassifier(**params, max_depth=4, colsample_bytree=0.8,
                                eval_metric="logloss", n_jobs=-1)
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        modele = GradientBoostingClassifier(**params, max_depth=3)
    modele.fit(X_train, y_train)
    return modele


def feature_importance_native(modele, features, top_n=15):
    print("\n1. Feature importance native ...")
    imp = pd.DataFrame({
        "feature": features,
        "importance": modele.feature_importances_
    }).sort_values("importance", ascending=False)

    imp.to_csv(DOSSIER_SORTIE / "importance_native.csv", index=False)

    top = imp.head(top_n)
    plt.figure(figsize=(9, 6))
    plt.barh(top["feature"][::-1], top["importance"][::-1], color="#1f77b4")
    plt.xlabel("Importance (native)")
    plt.title("Feature importance native — Gradient Boosting")
    plt.tight_layout()
    plt.savefig(DOSSIER_SORTIE / "importance_native.png", dpi=140)
    plt.close()
    print(f"   -> {DOSSIER_SORTIE / 'importance_native.png'}")
    return imp


def permutation_importance_test(modele, X_test, y_test, top_n=15):
    print("\n2. Permutation importance (sur le Test) ...")
    result = permutation_importance(
        modele, X_test, y_test,
        scoring="roc_auc", n_repeats=20, random_state=42, n_jobs=-1
    )
    imp = pd.DataFrame({
        "feature": X_test.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False)

    imp.to_csv(DOSSIER_SORTIE / "permutation_importance.csv", index=False)

    top = imp.head(top_n)
    plt.figure(figsize=(9, 6))
    plt.barh(top["feature"][::-1], top["importance_mean"][::-1],
             xerr=top["importance_std"][::-1], color="#2ca02c")
    plt.xlabel("Baisse du ROC-AUC quand la variable est mélangée")
    plt.title("Permutation importance — mesurée sur le Test")
    plt.tight_layout()
    plt.savefig(DOSSIER_SORTIE / "permutation_importance.png", dpi=140)
    plt.close()
    print(f"   -> {DOSSIER_SORTIE / 'permutation_importance.png'}")

    n_negatives = (imp["importance_mean"] < 0).sum()
    if n_negatives > 0:
        print(f"   [INFO] {n_negatives} variable(s) avec une importance négative : "
              f"le modèle fonctionne légèrement MIEUX sans elles (bruit).")
    return imp


def shap_analysis(modele, X_train, X_test, top_n=15):
    print("\n3. SHAP ...")
    try:
        import shap
    except ImportError:
        print("   [INFO] shap non installé - étape ignorée (pip install shap)")
        return None

    explainer = shap.TreeExplainer(modele)
    shap_values = explainer.shap_values(X_test)
    # Pour les classifieurs binaires, certaines versions renvoient une liste [classe0, classe1]
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    plt.figure()
    shap.summary_plot(shap_values, X_test, show=False, max_display=top_n)
    plt.tight_layout()
    plt.savefig(DOSSIER_SORTIE / "shap_summary.png", dpi=140, bbox_inches="tight")
    plt.close()
    print(f"   -> {DOSSIER_SORTIE / 'shap_summary.png'}")

    shap_moyen = pd.DataFrame({
        "feature": X_test.columns,
        "shap_abs_moyen": np.abs(shap_values).mean(axis=0)
    }).sort_values("shap_abs_moyen", ascending=False)
    shap_moyen.to_csv(DOSSIER_SORTIE / "shap_importance.csv", index=False)
    return shap_moyen


def comparer_les_trois(imp_native, imp_perm, imp_shap):
    print("\nComparaison des 3 méthodes (top 10 chacune) ...")
    lignes = ["# Tâche 59 — Comparaison des méthodes d'explicabilité\n"]
    lignes.append("## Feature importance native (Gradient Boosting)\n")
    for _, r in imp_native.head(10).iterrows():
        lignes.append(f"- {r['feature']} : {r['importance']:.4f}")
    lignes.append("\n## Permutation importance (Test)\n")
    for _, r in imp_perm.head(10).iterrows():
        lignes.append(f"- {r['feature']} : {r['importance_mean']:.4f} (+/- {r['importance_std']:.4f})")
    if imp_shap is not None:
        lignes.append("\n## SHAP (moyenne des valeurs absolues)\n")
        for _, r in imp_shap.head(10).iterrows():
            lignes.append(f"- {r['feature']} : {r['shap_abs_moyen']:.4f}")
    else:
        lignes.append("\n## SHAP\nNon disponible (shap non installé).\n")

    chemin = DOSSIER_SORTIE / "comparaison_explicabilite.md"
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    print(f"   -> {chemin}")


def main():
    print("=" * 75)
    print("TÂCHE 59 — EXPLICABILITÉ")
    print("=" * 75)

    X_train, X_test, y_train, y_test = charger_donnees()
    print(f"Train : {X_train.shape} | Test : {X_test.shape}")

    modele = entrainer_modele(X_train, y_train)
    auc = roc_auc_score(y_test, modele.predict_proba(X_test)[:, 1])
    print(f"ROC-AUC (rappel) : {auc:.4f}")

    imp_native = feature_importance_native(modele, X_train.columns)
    imp_perm = permutation_importance_test(modele, X_test, y_test)
    imp_shap = shap_analysis(modele, X_train, X_test)

    comparer_les_trois(imp_native, imp_perm, imp_shap)

    print("\n" + "=" * 75)
    print(f"Tâche 59 terminée — résultats dans {DOSSIER_SORTIE}/")
    print("=" * 75)


if __name__ == "__main__":
    main()