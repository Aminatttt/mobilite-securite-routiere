from pathlib import Path
import requests
import logging


# ============================================================
# CONFIGURATION
# ============================================================

YEARS = range(2020, 2025)

BASE_DIR = Path("data/raw/meteo")
LOG_DIR = Path("logs")

DATASET_URL = (
    "https://www.data.gouv.fr/api/1/datasets/"
    "donnees-climatologiques-de-base-horaires/"
)

TIMEOUT = 120


# ============================================================
# LOGS
# ============================================================

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

log_file = LOG_DIR / "download_meteo.log"

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

    response = requests.get(
        DATASET_URL,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()


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
    print("TELECHARGEMENT METEO-FRANCE")
    print("=" * 60)


    logger.info(
        "===== DEBUT METEO ====="
    )


    try:

        print(
            "\nConnexion à data.gouv.fr..."
        )

        dataset = get_dataset()

        print(
            "Source météo accessible ✅"
        )

        logger.info(
            "SOURCE_OK | METEO"
        )


    except Exception as e:

        print(
            f"Erreur source météo ❌ : {e}"
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


    # --------------------------------------------------------
    # Recherche des ressources concernant Paris / département 75
    # --------------------------------------------------------

    paris_resources = []


    for resource in resources:

        title = resource.get(
            "title",
            ""
        )

        description = resource.get(
            "description",
            ""
        )

        url = resource.get(
            "url",
            ""
        )


        text = (
            f"{title} "
            f"{description} "
            f"{url}"
        ).lower()


        if (
            "75" in text
            or "paris" in text
        ):

            if url:

                paris_resources.append(
                    resource
                )


    print(
        f"Ressources potentiellement Paris : "
        f"{len(paris_resources)}"
    )


    # --------------------------------------------------------
    # Téléchargement
    # --------------------------------------------------------

    for resource in paris_resources:

        url = resource.get(
            "url"
        )

        title = resource.get(
            "title",
            "meteo_75"
        )


        if not url:
            continue


        # On garde uniquement les ressources
        # couvrant notre période
        text = (
            f"{title} {url}"
        ).lower()


        if not any(
            str(year) in text
            for year in YEARS
        ):

            continue


        folder = BASE_DIR / "2020_2024"

        folder.mkdir(
            parents=True,
            exist_ok=True
        )


        filename = url.split("/")[-1]


        if not filename:
            filename = (
                "H_75_previous-2020-2024.csv.gz"
            )


        destination = folder / filename


        download_file(
            url,
            destination
        )


    logger.info(
        "===== FIN METEO ====="
    )


    print(
        "\n" + "=" * 60
    )

    print(
        "METEO TERMINEE ✅"
    )

    print(
        "=" * 60
    )


if __name__ == "__main__":
    main()