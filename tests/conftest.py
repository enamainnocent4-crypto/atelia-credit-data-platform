"""Outils partagés par les tests.

Les tests unitaires travaillent sur un PETIT jeu de données (800 demandes au lieu
de 8 000), généré une seule fois dans un dossier temporaire : rapide, et sans
jamais toucher aux données du projet.
"""

import pytest

from data_generator import config as cfg
from data_generator import generate

SMALL_N_APPLICATIONS = 800


@pytest.fixture(scope="session")
def small_dataset(tmp_path_factory):
    """Génère un petit jeu de données complet et renvoie son dossier."""
    output_dir = tmp_path_factory.mktemp("generated")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cfg, "OUTPUT_DIR", output_dir)
        mp.setattr(cfg, "N_APPLICATIONS", SMALL_N_APPLICATIONS)
        generate.main()
    return output_dir
