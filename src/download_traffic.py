from pathlib import Path
from datetime import datetime
import requests
import logging
import re


# ============================================================
# CONFIGURATION
# ============================================================

YEARS = range(2020, 2025)

BASE_DIR = Path("data/raw/traffic")
LOG_DIR = Path("logs")

DATASET_ID = "comptages-routiers-permanents-historique"

ATTACHMENTS_URL = (
    "https://opendata.paris.fr/api/explore/v2.1/"
    f"catalog/datasets/{DATASET_ID}/attachments"
)

TIMEOUT = 120


# ============================================================
# DOSSIERS
# ============================================================

BASE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOG
# ============================================================

log_file = LOG_DIR / "download_traffic.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# RECUPERATION DES PIECES JOINTES
# ============================================================

def get_attachments():

    response = requests.get(
        ATTACHMENTS_URL,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    return data


# ============================================================
# NETTOYAGE NOM FICHIER
# ============================================================

def clean_filename(filename):

    filename = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        filename
    )

    return filename.strip()


# ============================================================
# EXTRACTION NOM + URL
# ============================================================

def get_attachment_info(attachment):

    name = (
        attachment.get("name")
        or attachment.get("title")
        or attachment.get("filename")
        or attachment.get("id")
        or "traffic_file"
    )

    url = (
        attachment.get("href")
        or attachment.get("url")
        or attachment.get("download_url")
    )

    return name, url


# ============================================================
# TELECHARGEMENT
# ============================================================

def download_file(url, destination):

    # --------------------------------------------------------
    # Si le fichier existe déjà
    # --------------------------------------------------------

    if (
        destination.exists()
        and destination.stat().st_size > 0
    ):

        print(
            f"  Déjà présent : {destination.name}"
        )

        logger.info(
            f"SKIP | {destination}"
        )

        return True


    print(
        f"  Téléchargement : {destination.name}"
    )


    try:

        response = requests.get(
            url,
            timeout=TIMEOUT,
            stream=True
        )

        response.raise_for_status()


        # ----------------------------------------------------
        # Ecriture du fichier par morceaux
        # ----------------------------------------------------

        with open(
            destination,
            "wb"
        ) as file:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    file.write(chunk)


        # ----------------------------------------------------
        # Vérification taille
        # ----------------------------------------------------

        size_bytes = destination.stat().st_size

        size_mb = size_bytes / (1024 * 1024)


        if size_bytes == 0:

            print(
                "  ERREUR : fichier vide ❌"
            )

            logger.error(
                f"EMPTY_FILE | {destination}"
            )

            destination.unlink()

            return False


        print(
            f"  OK : {size_mb:.2f} MB ✅"
        )


        logger.info(
            f"DOWNLOAD_OK | {destination} | "
            f"{size_mb:.2f} MB"
        )


        return True


    except Exception as e:

        print(
            f"  ERREUR : {e} ❌"
        )


        logger.error(
            f"DOWNLOAD_ERROR | {url} | {e}"
        )


        # Si téléchargement incomplet
        if destination.exists():
            destination.unlink()


        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TELECHARGEMENT TRAFIC PARIS")
    print("=" * 60)


    logger.info(
        "=================================================="
    )

    logger.info(
        "DEBUT TELECHARGEMENT TRAFIC PARIS"
    )


    # ========================================================
    # CONNEXION API
    # ========================================================

    print(
        "\nConnexion à Paris Open Data..."
    )


    try:

        data = get_attachments()


        print(
            "API trafic accessible ✅"
        )


        logger.info(
            "SOURCE_OK | PARIS_OPEN_DATA"
        )


    except Exception as e:

        print(
            f"Erreur API trafic ❌ : {e}"
        )


        logger.error(
            f"SOURCE_ERROR | {e}"
        )


        return


    # ========================================================
    # RECUPERATION DES PIECES JOINTES
    # ========================================================

    # L'API peut retourner directement une liste
    # ou un objet contenant "attachments".

    if isinstance(data, list):

        attachments = data

    elif isinstance(data, dict):

        attachments = data.get(
            "attachments",
            []
        )

    else:

        attachments = []


    print(
        f"\nPièces jointes trouvées : "
        f"{len(attachments)}"
    )


    logger.info(
        f"ATTACHMENTS_FOUND | count={len(attachments)}"
    )


    # ========================================================
    # DEBUG : AFFICHER LES PREMIERES PIECES JOINTES
    # ========================================================

    if len(attachments) > 0:

        print(
            "\n--- Aperçu des premières pièces jointes ---"
        )


        for attachment in attachments[:5]:

            print(
                attachment
            )


        print(
            "--- Fin aperçu ---\n"
        )


    else:

        print(
            "\n⚠️ Aucune pièce jointe trouvée."
        )

        print(
            "La structure retournée par l'API est :"
        )

        print(
            data
        )


        logger.warning(
            "NO_ATTACHMENTS"
        )


    # ========================================================
    # BOUCLE PAR ANNEE
    # ========================================================

    for year in YEARS:

        print(
            f"\n===== ANNEE {year} ====="
        )


        logger.info(
            f"START_YEAR | {year}"
        )


        # ----------------------------------------------------
        # Création du dossier
        # ----------------------------------------------------

        folder = (
            BASE_DIR / str(year)
        )


        folder.mkdir(
            parents=True,
            exist_ok=True
        )


        year_count = 0


        # ----------------------------------------------------
        # Recherche des fichiers de l'année
        # ----------------------------------------------------

        for attachment in attachments:

            name, url = get_attachment_info(
                attachment
            )


            # Si pas d'URL
            if not url:
                continue


            # Texte utilisé pour rechercher l'année

            text = (
                f"{name} {url}"
            ).lower()


            # ------------------------------------------------
            # On garde uniquement l'année recherchée
            # ------------------------------------------------

            if str(year) not in text:

                continue


            # ------------------------------------------------
            # Nettoyage du nom
            # ------------------------------------------------

            filename = clean_filename(
                str(name)
            )


            # ------------------------------------------------
            # Si pas d'extension
            # ------------------------------------------------

            if "." not in filename:

                filename += ".txt"


            destination = (
                folder / filename
            )


            # ------------------------------------------------
            # Téléchargement
            # ------------------------------------------------

            success = download_file(
                url,
                destination
            )


            if success:

                year_count += 1


        # ----------------------------------------------------
        # Résultat année
        # ----------------------------------------------------

        print(
            f"Fichiers téléchargés/trouvés : "
            f"{year_count}"
        )


        logger.info(
            f"END_YEAR | {year} | "
            f"files={year_count}"
        )


    # ========================================================
    # FIN
    # ========================================================

    logger.info(
        "FIN TELECHARGEMENT TRAFIC PARIS"
    )


    print(
        "\n" + "=" * 60
    )

    print(
        "TRAFIC TERMINE ✅"
    )

    print(
        "=" * 60
    )


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    main()