
from pathlib import Path
from datetime import datetime
import requests
import logging
import re


# ============================================================
# CONFIGURATION
# ============================================================

YEARS = range(2020, 2025)

BASE_DIR = Path("data/raw/baac")
LOG_DIR = Path("logs")

DATASET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "bases-de-donnees-annuelles-des-accidents-corporels-"
    "de-la-circulation-routiere-annees-de-2005-a-2024/"
)

TIMEOUT = 60


# ============================================================
# LOGS
# ============================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)

log_file = LOG_DIR / "download_baac.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# FONCTIONS
# ============================================================

def get_dataset():
    """
    Récupère les métadonnées du dataset BAAC depuis data.gouv.fr.
    """

    response = requests.get(
        DATASET_URL,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()


def download_file(url, destination):
    """
    Télécharge un fichier uniquement s'il n'existe pas déjà.
    """

    if destination.exists() and destination.stat().st_size > 0:
        print(f"  Déjà présent : {destination.name}")
        logger.info(f"SKIP | {destination}")
        return True

    print(f"  Téléchargement : {destination.name}")

    try:
        response = requests.get(
            url,
            timeout=TIMEOUT,
            stream=True
        )

        response.raise_for_status()

        with open(destination, "wb") as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    file.write(chunk)

        size_mb = destination.stat().st_size / (1024 * 1024)

        print(f"  OK : {size_mb:.2f} MB")

        logger.info(
            f"DOWNLOAD_OK | {destination} | {size_mb:.2f} MB"
        )

        return True

    except Exception as e:

        print(f"  ERREUR : {e}")

        logger.error(
            f"DOWNLOAD_ERROR | {url} | {e}"
        )

        if destination.exists():
            destination.unlink()

        return False


def find_baac_resources(dataset, year):
    """
    Recherche les ressources CSV correspondant à l'année.
    """

    resources = dataset.get("resources", [])

    year_resources = []

    for resource in resources:

        url = resource.get("url", "")
        title = resource.get("title", "")
        description = resource.get("description", "")

        text = f"{url} {title} {description}".lower()

        if str(year) not in text:
            continue

        if ".csv" not in url.lower():
            continue

        year_resources.append(resource)

    return year_resources


def classify_baac_file(resource):
    """
    Essaie d'identifier le type de fichier BAAC.
    """

    text = (
        f"{resource.get('title', '')} "
        f"{resource.get('description', '')} "
        f"{resource.get('url', '')}"
    ).lower()

    if "caracter" in text or "caract" in text:
        return "caracteristiques"

    if "lieux" in text:
        return "lieux"

    if "vehicul" in text:
        return "vehicules"

    if "usager" in text:
        return "usagers"

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TELECHARGEMENT AUTOMATISE BAAC")
    print("=" * 60)

    logger.info("===== DEBUT BAAC =====")

    try:

        print("\nConnexion à data.gouv.fr...")

        dataset = get_dataset()

        print("Source BAAC accessible ✅")

        logger.info("SOURCE_OK | BAAC")

    except Exception as e:

        print(f"Erreur accès BAAC ❌ : {e}")

        logger.error(f"SOURCE_ERROR | {e}")

        return


    for year in YEARS:

        print(f"\n===== ANNEE {year} =====")

        folder = BASE_DIR / str(year)

        folder.mkdir(
            parents=True,
            exist_ok=True
        )

        resources = find_baac_resources(
            dataset,
            year
        )

        print(
            f"Ressources CSV trouvées : {len(resources)}"
        )

        logger.info(
            f"YEAR {year} | resources={len(resources)}"
        )

        if not resources:

            print(
                f"ATTENTION : aucune ressource trouvée pour {year}"
            )

            logger.warning(
                f"NO_RESOURCES | {year}"
            )

            continue


        downloaded_types = set()

        for resource in resources:

            url = resource.get("url")

            if not url:
                continue

            file_type = classify_baac_file(
                resource
            )

            if file_type is None:

                # fallback avec le nom de la ressource
                title = resource.get(
                    "title",
                    f"baac_{year}"
                )

                safe_title = re.sub(
                    r"[^a-zA-Z0-9_-]",
                    "_",
                    title
                )

                filename = f"{safe_title}.csv"

            else:

                filename = (
                    f"baac_{year}_{file_type}.csv"
                )

            destination = folder / filename

            success = download_file(
                url,
                destination
            )

            if success and file_type:

                downloaded_types.add(
                    file_type
                )


        print(
            "Types BAAC identifiés :",
            ", ".join(sorted(downloaded_types))
            if downloaded_types
            else "aucun"
        )


    logger.info("===== FIN BAAC =====")

    print("\n" + "=" * 60)
    print("BAAC TERMINE ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()