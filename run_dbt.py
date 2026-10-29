"""Lance dbt avec les identifiants du fichier .env.

dbt lit ses identifiants dans des variables d'environnement (voir dbt/profiles.yml).
Ce petit lanceur les charge depuis .env, puis transmet la commande à dbt.

Exemples, depuis la racine du projet :
    python run_dbt.py debug            # vérifier la connexion
    python run_dbt.py build            # créer les modèles et lancer les tests
    python run_dbt.py source freshness # vérifier la fraîcheur des sources
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
os.environ["DBT_PROJECT_DIR"] = str(ROOT / "dbt")
os.environ["DBT_PROFILES_DIR"] = str(ROOT / "dbt")

# Le programme dbt installé dans le même environnement que ce Python
dbt_exe = Path(sys.executable).with_name("dbt.exe" if os.name == "nt" else "dbt")
sys.exit(subprocess.call([str(dbt_exe), *sys.argv[1:]]))
