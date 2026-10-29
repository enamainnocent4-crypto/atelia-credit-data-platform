"""Simule une mise à jour du CRM : des clients déménagent, d'autres changent de revenu.

Sert à démontrer l'historisation des clients (SCD de type 2) : dbt garde
l'ancienne version de chaque client modifié, avec ses dates de validité.

Le script est IDEMPOTENT : la première fois, il sauvegarde l'export d'origine
(customers_v1.csv) ; ensuite, il recalcule toujours la même version 2 à partir
de cette sauvegarde. Le relancer ne modifie donc pas les clients une deuxième fois.

Lancement, depuis la racine du projet :
    python -m data_generator.crm_update
"""

from __future__ import annotations

import shutil

import numpy as np
import pandas as pd

from data_generator import config as cfg
from data_generator.generate import POSTCODE_PREFIX

UPDATE_SEED = 2026
MOVE_RATE = 0.03        # 3 % des clients déménagent
INCOME_RATE = 0.05      # 5 % déclarent un nouveau revenu


def main() -> None:
    crm_dir = cfg.OUTPUT_DIR / "crm"
    current, original = crm_dir / "customers.csv", crm_dir / "customers_v1.csv"
    if not current.exists():
        raise FileNotFoundError("Lancez d'abord : python -m data_generator.generate")
    if not original.exists():
        shutil.copy(current, original)  # sauvegarde unique de la version 1

    rng = np.random.default_rng(UPDATE_SEED)
    df = pd.read_csv(original, dtype=str, keep_default_na=False)
    n = len(df)
    cities = sorted(POSTCODE_PREFIX)

    # Déménagements : nouvelle ville et nouveau code postal (l'agence de rattachement ne change pas)
    movers = rng.choice(n, int(n * MOVE_RATE), replace=False)
    for i in movers:
        new_city = str(rng.choice([c for c in cities if c != df.at[i, "city"]]))
        df.at[i, "city"] = new_city
        df.at[i, "postal_code"] = f"{POSTCODE_PREFIX[new_city]}0{int(rng.integers(0, 100)):02d}"

    # Nouveaux revenus déclarés : de -20 % à +25 %
    earners = rng.choice(n, int(n * INCOME_RATE), replace=False)
    for i in earners:
        factor = rng.uniform(0.80, 1.25)
        df.at[i, "monthly_income"] = str(int(round(int(df.at[i, "monthly_income"]) * factor, -1)))

    df.to_csv(current, index=False, encoding="utf-8")
    changed = len(set(movers) | set(earners))
    print(f"Mise à jour CRM : {len(movers)} déménagements, {len(earners)} nouveaux revenus, "
          f"{changed} clients modifiés sur {n}.")
    print("Étapes suivantes : python -m ingestion.run --only csv   puis   python run_dbt.py build")


if __name__ == "__main__":
    main()
