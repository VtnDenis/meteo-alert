# meteo_alert

Surveillance météo horaire de **Saint-Chamond (42400)** sur la date cible `2026-04-11` via **Open-Meteo**.

Règle d’alerte:

- créneaux `matin` (06:00–11:59) et `après-midi` (12:00–17:59), fuseau `Europe/Paris` ;
- si précipitation horaire `> 0 mm`, envoi d’un email via Resend ;
- anti-duplication: **1 email max par créneau** via clé d’idempotence Resend.

## Variables d’environnement

Copier `.env.example` vers `.env`, puis renseigner:

- `OPEN_METEO_BASE_URL` (optionnel, défaut: `https://api.open-meteo.com/v1/forecast`)
- `OPEN_METEO_MODEL` (optionnel, défaut: `auto`)
- `OPEN_METEO_TIMEOUT_SECONDS` (optionnel, défaut: `30`)
- `RESEND_API_KEY`
- `RESEND_FROM`

`ALERT_EMAIL_TO` est prérempli avec `vtndenis@gmail.com`.

L’intégration actuelle utilise l’offre Open-Meteo non commerciale (sans clé API).

## Exécution locale

1. Créer et activer un environnement virtuel local `venv`.
2. Installer les dépendances avec `pip install -r requirements.txt`.
3. Lancer: `python main.py`.

## GitHub Actions

Workflow: `.github/workflows/weather-alert.yml`

Secrets attendus:

- `RESEND_API_KEY`
- `RESEND_FROM`

Variables d’environnement workflow utiles:

- `OPEN_METEO_BASE_URL`
- `OPEN_METEO_MODEL`
- `OPEN_METEO_TIMEOUT_SECONDS`

Le workflow est planifié toutes les heures (cron) et déclenchable manuellement.

## Tests

Lancer les tests avec `pytest`.

## Attribution des données météo

Les données météo proviennent de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
