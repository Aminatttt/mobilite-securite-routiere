from pathlib import Path
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    roc_auc_score, roc_curve, average_precision_score, precision_recall_curve,
    confusion_matrix, precision_score, recall_score, f1_score,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_5253 = BASE_DIR / "output" / "tache_52_53"
DOSSIER_SORTIE = BASE_DIR / "output" / "tache_58"
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


def metriques(y_test, y_probs, nom, seuil=0.5):
    y_pred = (y_probs >= seuil).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
    return {
        "modele": nom, "seuil": seuil,
        "roc_auc": round(roc_auc_score(y_test, y_probs), 4),
        "pr_auc": round(average_precision_score(y_test, y_probs), 4),
        "precision_grave": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall_grave": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "f1_grave": round(f1_score(y_test, y_pred, zero_division=0), 4),
        "TN": tn, "FP": fp, "FN": fn, "TP": tp,
    }


def main():

    X_train, X_test, y_train, y_test = charger_donnees()

    # --- Entraînement des 3 modèles à comparer ---
    scaler = StandardScaler().fit(X_train)
    modele_lr = LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)
    modele_lr.fit(scaler.transform(X_train), y_train)

    modele_gb_brut = entrainer_gradient_boosting(X_train, y_train)

    poids = compute_sample_weight(class_weight="balanced", y=y_train)
    modele_gb_pondere = entrainer_gradient_boosting(X_train, y_train, sample_weight=poids)

    modeles = {
        "1. Regression Logistique": modele_lr.predict_proba(scaler.transform(X_test))[:, 1],
        "2. Gradient Boosting (brut)": modele_gb_brut.predict_proba(X_test)[:, 1],
        "3. Gradient Boosting + class_weight": modele_gb_pondere.predict_proba(X_test)[:, 1],
    }

    # --- Métriques + courbes, dans la même boucle ---
    resultats = []
    plt.figure("roc", figsize=(7, 6))
    plt.figure("pr", figsize=(7, 6))

    for nom, y_probs in modeles.items():
        resultats.append(metriques(y_test, y_probs, nom))

        fpr, tpr, _ = roc_curve(y_test, y_probs)
        plt.figure("roc")
        plt.plot(fpr, tpr, label=f"{nom} (AUC={roc_auc_score(y_test, y_probs):.3f})")

        p, r, _ = precision_recall_curve(y_test, y_probs)
        plt.figure("pr")
        plt.plot(r, p, label=f"{nom} (PR-AUC={average_precision_score(y_test, y_probs):.3f})")

    plt.figure("roc")
    plt.plot([0, 1], [0, 1], "--", color="gray", label="Hasard")
    plt.xlabel("Taux de faux positifs"); plt.ylabel("Recall"); plt.title("Courbes ROC")
    plt.legend(); plt.tight_layout()
    plt.savefig(DOSSIER_SORTIE / "courbes_roc.png", dpi=120)

    plt.figure("pr")
    plt.axhline(y_test.mean(), linestyle="--", color="gray", label="Hasard")
    plt.xlabel("Recall"); plt.ylabel("Précision"); plt.title("Courbes Précision-Rappel")
    plt.legend(); plt.tight_layout()
    plt.savefig(DOSSIER_SORTIE / "courbes_precision_rappel.png", dpi=120)

    # --- Tableau comparatif ---
    df = pd.DataFrame(resultats)
    print(df.to_string(index=False))
    df.to_csv(DOSSIER_SORTIE / "metriques_comparaison.csv", index=False)

    meilleur = df.loc[df["f1_grave"].idxmax()]
    print(f"\n Meilleur modèle : {meilleur['modele']} (F1={meilleur['f1_grave']})")
    print(f" Résultats dans {DOSSIER_SORTIE}")


if __name__ == "__main__":
    main()