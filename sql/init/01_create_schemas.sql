-- Couches de la plateforme décisionnelle Atelia Crédit.
-- Exécuté automatiquement par PostgreSQL à la toute première création de la base.

CREATE SCHEMA IF NOT EXISTS raw;      -- données brutes, telles que reçues des sources (CSV, API)
CREATE SCHEMA IF NOT EXISTS staging;  -- données nettoyées et typées (dbt)
CREATE SCHEMA IF NOT EXISTS marts;    -- modèle en étoile consommé par Power BI (dbt)
