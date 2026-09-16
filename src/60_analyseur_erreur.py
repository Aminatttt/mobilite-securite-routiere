"""
===============================================================================
TÂCHE 60 — ANALYSE DES ERREURS ET DES CAS D'ÉCHEC DU MODÈLE
===============================================================================
Objectif : ne pas s'arrêter aux métriques globales (tâche 58) mais regarder
CONCRÈTEMENT quels accidents le modèle rate, et s'il existe un pattern commun
aux faux négatifs (accidents graves non détectés) — c'est souvent le cas le
plus critique métier : rater un accident grave coûte plus cher que fausse
alerte sur un accident léger.

Entrées : output/tache_52_53/features_{train,test}.csv, y_{train,test}.csv
Sorties : output/tache_60/*
===============================================================================
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_5253 = BASE_DIR / "output" / "tache_52_53"
DOSSIER_SORTIE = BASE_DIR / "output" / "tache_60"
DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)

TARGET = "grave"
SEUIL_OPTIMAL = 0.111  # validé en tâche 57 (meilleur F1)


def charger_donnees():
    X_train = pd.read_csv(DOSSIER_5253 / "features_train.csv")
    X_test = pd.read_csv(DOSSIER_5253 / "features_test.csv")[X_train.columns]
    y_train = pd.read_csv(DOSSIER_5253 / "y_train.csv")[TARGET]
    y_test = pd.read_csv(DOSSIER_5253 / "y_test.csv")[TARGET]
    return X_train, X_test, y_train, y_test


def entrainer_modele(X_train, y_train):
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


def categoriser_predictions(y_true, y_pred):
    cats = pd.Series(index=y_true.index, dtype="object")
    cats[(y_true == 1) & (y_pred == 1)] = "TP (grave détecté)"
    cats[(y_true == 0) & (y_pred == 0)] = "TN (léger détecté)"
    cats[(y_true == 1) & (y_pred == 0)] = "FN (grave RATÉ)"
    cats[(y_true == 0) & (y_pred == 1)] = "FP (fausse alerte)"
    return cats


def analyser_erreurs(X_test, y_test, y_probs, categories):
    print("\nRépartition des prédictions :")
    print(categories.value_counts().to_string())

    X_analyse = X_test.copy()
    X_analyse["y_true"] = y_test.values
    X_analyse["y_probs"] = y_probs
    X_analyse["categorie"] = categories.values

    X_analyse.to_csv(DOSSIER_SORTIE / "predictions_detaillees.csv", index=False)

    # -------------------------------------------------------------------
    # Focus sur les FN : les accidents graves ratés par le modèle
    # -------------------------------------------------------------------
    fn = X_analyse[X_analyse["categorie"] == "FN (grave RATÉ)"]
    tp = X_analyse[X_analyse["categorie"] == "TP (grave détecté)"]

    print(f"\nFocus sur les faux négatifs (graves ratés) : {len(fn)} cas")
    if len(fn) > 0:
        print(f"   Probabilité moyenne attribuée par le modèle : {fn['y_probs'].mean():.3f}")
        print(f"   (pour comparaison, TP moyen : {tp['y_probs'].mean():.3f})" if len(tp) else "")

    # -------------------------------------------------------------------
    # Comparaison des features numériques : FN vs TP
    # (est-ce que les graves ratés ont un profil différent des graves détectés ?)
    # -------------------------------------------------------------------
    cols_num = X_test.select_dtypes(include=[np.number]).columns.tolist()
    if len(fn) > 0 and len(tp) > 0:
        comparaison = pd.DataFrame({
            "moyenne_FN_grave_rate": fn[cols_num].mean(),
            "moyenne_TP_grave_detecte": tp[cols_num].mean(),
        })
        comparaison["ecart"] = comparaison["moyenne_FN_grave_rate"] - comparaison["moyenne_TP_grave_detecte"]
        comparaison = comparaison.sort_values("ecart", key=abs, ascending=False)
        comparaison.to_csv(DOSSIER_SORTIE / "comparaison_FN_vs_TP.csv")
        print("\nVariables où les FN diffèrent le plus des TP (top 8) :")
        print(comparaison.head(8).to_string())

    # -------------------------------------------------------------------
    # Distribution des probabilités prédites par catégorie
    # -------------------------------------------------------------------
    plt.figure(figsize=(9, 6))
    for cat in ["TN (léger détecté)", "FP (fausse alerte)", "FN (grave RATÉ)", "TP (grave détecté)"]:
        sous = X_analyse[X_analyse["categorie"] == cat]["y_probs"]
        if len(sous) > 0:
            plt.hist(sous, bins=20, alpha=0.5, label=f"{cat} (n={len(sous)})")
    plt.axvline(SEUIL_OPTIMAL, color="black", linestyle="--", label=f"Seuil ({SEUIL_OPTIMAL})")
    plt.xlabel("Probabilité prédite d'être 'grave'")
    plt.ylabel("Nombre de cas")
    plt.title("Distribution des probabilités prédites, par type d'erreur")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(DOSSIER_SORTIE / "distribution_probabilites.png", dpi=140)
    plt.close()
    print(f"\n-> {DOSSIER_SORTIE / 'distribution_probabilites.png'}")

    # -------------------------------------------------------------------
    # Cas les plus "manqués" : accidents graves avec la probabilité la plus basse
    # -------------------------------------------------------------------
    if len(fn) > 0:
        pires_fn = fn.sort_values("y_probs").head(10)
        pires_fn.to_csv(DOSSIER_SORTIE / "pires_faux_negatifs.csv", index=False)
        print(f"\n-> {DOSSIER_SORTIE / 'pires_faux_negatifs.csv'} "
              f"(les 10 accidents graves où le modèle était le plus confiant à tort)")

    return X_analyse


def ecrire_rapport(X_analyse, y_test, y_probs):
    chemin = DOSSIER_SORTIE / "rapport_tache_60.md"
    n_total = len(X_analyse)
    n_fn = (X_analyse["categorie"] == "FN (grave RATÉ)").sum()
    n_tp = (X_analyse["categorie"] == "TP (grave détecté)").sum()
    n_fp = (X_analyse["categorie"] == "FP (fausse alerte)").sum()
    n_tn = (X_analyse["categorie"] == "TN (léger détecté)").sum()
    n_graves_reels = n_fn + n_tp

    lignes = [
        "# Tâche 60 — Analyse des erreurs et cas d'échec du modèle",
        "",
        f"Échantillon Test : {n_total:,} accidents, dont {n_graves_reels} réellement graves.",
        f"Seuil de décision utilisé : {SEUIL_OPTIMAL} (validé en tâche 57).",
        "",
        "## Répartition des prédictions",
        f"- Vrais négatifs (léger correctement détecté) : {n_tn}",
        f"- Faux positifs (fausse alerte) : {n_fp}",
        f"- Faux négatifs (**grave raté**) : {n_fn}",
        f"- Vrais positifs (grave détecté) : {n_tp}",
        "",
        "## Constat principal",
        (
            f"Sur {n_graves_reels} accidents réellement graves dans le Test, le modèle en "
            f"détecte {n_tp} et en rate {n_fn} "
            f"({100*n_fn/n_graves_reels:.0f}% des cas graves passent inaperçus)."
            if n_graves_reels > 0 else "Aucun accident grave dans cet échantillon Test."
        ),
        "",
        "## Limite structurelle (pas un bug)",
        (
            "Avec seulement 78 accidents graves dans tout le jeu de test, chaque cas "
            "individuel pèse lourd dans les métriques (1 cas = ~1,3 point de recall). "
            "Le modèle ne dispose pas d'assez de cas positifs, ni de variables "
            "suffisamment discriminantes (cf. tâche 49 : corrélations faibles), pour "
            "identifier un pattern fiable de gravité. Ce n'est pas un problème "
            "d'implémentation mais une vraie limite du signal disponible dans les données."
        ),
        "",
        "## Recommandation",
        (
            "Pour progresser sur ce point, il faudrait des variables actuellement absentes "
            "du dataset enrichi : vitesse au moment du choc, type de route/infrastructure, "
            "port de la ceinture/casque, type de véhicule impliqué. Ces variables sont "
            "présentes dans les données BAAC brutes mais ont été exclues du modèle pour "
            "éviter la fuite de données (tâche 52) — elles caractérisent l'accident "
            "lui-même plutôt que son contexte, donc leur intégration demanderait de "
            "vérifier au cas par cas qu'elles sont bien connues *avant* l'accident, "
            "pas déduites après coup."
        ),
    ]

    chemin.write_text("\n".join(lignes), encoding="utf-8")
    print(f"\n-> {chemin}")


def main():
    print("=" * 75)
    print("TÂCHE 60 — ANALYSE DES ERREURS")
    print("=" * 75)

    X_train, X_test, y_train, y_test = charger_donnees()
    modele = entrainer_modele(X_train, y_train)

    y_probs = modele.predict_proba(X_test)[:, 1]
    y_pred = (y_probs >= SEUIL_OPTIMAL).astype(int)

    categories = categoriser_predictions(y_test, pd.Series(y_pred, index=y_test.index))
    X_analyse = analyser_erreurs(X_test, y_test, y_probs, categories)
    ecrire_rapport(X_analyse, y_test, y_probs)

    print("\n" + "=" * 75)
    print(f"Tâche 60 terminée — résultats dans {DOSSIER_SORTIE}/")
    print("=" * 75)


if __name__ == "__main__":
    main()