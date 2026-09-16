from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    roc_auc_score, average_precision_score, precision_recall_curve,
    precision_score, recall_score, f1_score, confusion_matrix,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_5253 = BASE_DIR / "output" / "tache_52_53"
DOSSIER_SORTIE = BASE_DIR / "output" / "tache_57"
DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
TARGET = "grave"

def charger_donnees():
    X_train = pd.read_csv(DOSSIER_5253 / "features_train.csv")
    X_test = pd.read_csv(DOSSIER_5253 / "features_test.csv")[X_train.columns]
    y_train = pd.read_csv(DOSSIER_5253 / "y_train.csv")[TARGET]
    y_test = pd.read_csv(DOSSIER_5253 / "y_test.csv")[TARGET]
    return X_train, X_test, y_train, y_test


def entrainer_gradient_boosting(X_train, y_train, sample_weight=None):
    """XGBoost si installé, sinon GradientBoostingClassifier (sklearn)."""
    params = dict(n_estimators=300, learning_rate=0.05, subsample=0.8, random_state=42)
    try:
        from xgboost import XGBClassifier
        modele = XGBClassifier(**params, max_depth=4, colsample_bytree=0.8,
                                eval_metric="logloss", n_jobs=-1)
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        modele = GradientBoostingClassifier(**params, max_depth=3)
    modele.fit(X_train, y_train, sample_weight=sample_weight)
    return modele


def metriques(y_test, y_probs, seuil, nom):
    y_pred = (y_probs >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    return {
        "strategie": nom, "seuil": round(seuil, 3),
        "roc_auc": round(roc_auc_score(y_test, y_probs), 4),
        "pr_auc": round(average_precision_score(y_test, y_probs), 4),
        "precision_grave": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall_grave": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_grave": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "TN": tn, "FP": fp, "FN": fn, "TP": tp,
    }

def seuil_optimal_f1(y_true, y_probs):
    p, r, seuils = precision_recall_curve(y_true, y_probs)
    p, r = p[:-1], r[:-1]
    f1 = np.where((p + r) > 0, 2 * p * r / (p + r), 0)
    return seuils[np.argmax(f1)]


def main():

    X_train, X_test, y_train, y_test = charger_donnees()
    print(f"Grave dans Train : {y_train.mean()*100:.1f}%")

    # --- Modèle de référence (brut), réutilisé pour le seuil optimal ---
    modele_brut = entrainer_gradient_boosting(X_train, y_train)
    y_probs_brut = modele_brut.predict_proba(X_test)[:, 1]

    resultats = [metriques(y_test, y_probs_brut, 0.5, "A. Brut")]

    # --- Stratégies de pondération : (nom, sample_weight) ---
    poids_balance = compute_sample_weight(class_weight="balanced", y=y_train)
    strategies = [("B. Class_weight", poids_balance)]

    for nom, poids in strategies:
        modele = entrainer_gradient_boosting(X_train, y_train, sample_weight=poids)
        y_probs = modele.predict_proba(X_test)[:, 1]
        resultats.append(metriques(y_test, y_probs, 0.5, nom))

    # --- Seuil optimal (cherché sur Train, appliqué au modèle brut) ---
    seuil_opt = seuil_optimal_f1(y_train, modele_brut.predict_proba(X_train)[:, 1])
    resultats.append(metriques(y_test, y_probs_brut, seuil_opt, f"C. Seuil optimal ({seuil_opt:.3f})"))

    # --- Comparaison ---
    df = pd.DataFrame(resultats)
    print(f"\n{df.to_string(index=False)}")
    df.to_csv(DOSSIER_SORTIE / "comparaison_strategies.csv", index=False)

    meilleure = df.loc[df["f1_grave"].idxmax()]
    print(f"\n Meilleure stratégie : {meilleure['strategie']} (F1={meilleure['f1_grave']})")
    print(f"\n Résultats dans {DOSSIER_SORTIE}")


if __name__ == "__main__":
    main()