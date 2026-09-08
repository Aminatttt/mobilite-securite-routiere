from pathlib import Path
import requests
import logging


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path("data/raw/population")
LOG_DIR = Path("logs")

DATASET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "populations-municipales-de-1968-a-2023/"
)

TIMEOUT = 120


# ============================================================
# LOGS
# ============================================================

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

log_file = LOG_DIR / "download_population.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# DOWNLOAD
# ============================================================

def download_file(url, destination):

    if (
        destination.exists()
        and destination.stat().st_size > 0
    ):

        print(
            f"Déjà présent : {destination.name}"
        )

        logger.info(
            f"SKIP | {destination}"
        )

        return True


    print(
        f"Téléchargement : {destination.name}"
    )


    try:

        response = requests.get(
            url,
            timeout=TIMEOUT,
            stream=True
        )

        response.raise_for_status()


        with open(
            destination,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    file.write(chunk)


        size_mb = (
            destination.stat().st_size
            / (1024 * 1024)
        )


        print(
            f"OK : {size_mb:.2f} MB"
        )


        logger.info(
            f"DOWNLOAD_OK | {destination} | "
            f"{size_mb:.2f} MB"
        )


        return True


    except Exception as e:

        print(
            f"ERREUR : {e}"
        )

        logger.error(
            f"DOWNLOAD_ERROR | {url} | {e}"
        )


        if destination.exists():
            destination.unlink()


        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TELECHARGEMENT POPULATION INSEE")
    print("=" * 60)


    logger.info(
        "===== DEBUT POPULATION ====="
    )


    try:

        print(
            "\nConnexion à data.gouv.fr..."
        )


        response = requests.get(
            DATASET_URL,
            timeout=TIMEOUT
        )


        response.raise_for_status()


        dataset = response.json()


        print(
            "Source INSEE accessible ✅"
        )


        logger.info(
            "SOURCE_OK | INSEE_POPULATION"
        )


    except Exception as e:

        print(
            f"Erreur source INSEE ❌ : {e}"
        )


        logger.error(
            f"SOURCE_ERROR | {e}"
        )


        return


    resources = dataset.get(
        "resources",
        []
    )


    print(
        f"Ressources trouvées : "
        f"{len(resources)}"
    )


    for resource in resources:

        url = resource.get(
            "url"
        )


        title = resource.get(
            "title",
            "population_insee"
        )


        if not url:
            continue


        print(
            f"\nRessource : {title}"
        )


        folder = BASE_DIR


        folder.mkdir(
            parents=True,
            exist_ok=True
        )


        # Garder le nom fourni par la source
        filename = url.split("/")[-1]


        if not filename:

            filename = (
                "population_insee_1968_2023"
            )


        destination = (
            folder / filename
        )


        download_file(
            url,
            destination
        )


    logger.info(
        "===== FIN POPULATION ====="
    )


    print(
        "\n" + "=" * 60
    )


    print(
        "POPULATION TERMINEE ✅"
    )


    print(
        "NB : la série INSEE utilisée va "
        "jusqu'à 2023."
    )


    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()