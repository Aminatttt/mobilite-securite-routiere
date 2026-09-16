from pathlib import Path
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, confusion_matrix, classification_report

BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_5253 = BASE_DIR / "output" / "tache_52_53"
DOSSIER_SORTIE = BASE_DIR / "output" / "tache_56"
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

def main():

    X_train, X_test, y_train, y_test = charger_donnees()
    print(f"Train : {X_train.shape} | Test : {X_test.shape}")

    modele = entrainer_gradient_boosting(X_train, y_train)
    y_probs = modele.predict_proba(X_test)[:, 1]
    y_pred = (y_probs >= 0.5).astype(int)

    print(f"\nROC-AUC = {roc_auc_score(y_test, y_probs):.4f}  (Baseline Tâche 55 ≈ 0.5345)")
    print(f"PR-AUC  = {average_precision_score(y_test, y_probs):.4f}")
    print(f"\nMatrice de confusion :\n{confusion_matrix(y_test, y_pred)}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Léger (0)', 'Grave (1)'])}")

    if hasattr(modele, "feature_importances_"):
        imp = pd.DataFrame({
            "feature": X_train.columns, "importance": modele.feature_importances_
        }).sort_values("importance", ascending=False)
        imp.to_csv(DOSSIER_SORTIE / "importance_features.csv", index=False)
        print(f"\nTop 10 features :\n{imp.head(10).to_string(index=False)}")

    pd.DataFrame({"y_test": y_test, "y_probs": y_probs, "y_pred": y_pred}) \
        .to_csv(DOSSIER_SORTIE / "predictions_test.csv", index=False)

    print(f"\n Résultats dans {DOSSIER_SORTIE}")


if __name__ == "__main__":
    main()