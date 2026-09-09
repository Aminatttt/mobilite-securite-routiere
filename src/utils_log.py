import logging
import os

def creer_logger(nom_script, dossier_script):
    dossier_logs = os.path.join(dossier_script, "logs")
    os.makedirs(dossier_logs, exist_ok=True)
    chemin_log = os.path.join(dossier_logs, f"{nom_script}.log")

    logger = logging.getLogger(nom_script)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler_fichier = logging.FileHandler(chemin_log, encoding="utf-8")
        handler_console = logging.StreamHandler()
        format_log = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler_fichier.setFormatter(format_log)
        handler_console.setFormatter(format_log)
        logger.addHandler(handler_fichier)
        logger.addHandler(handler_console)

    return logger