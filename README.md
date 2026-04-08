# meteo_alert

Surveillance météo horaire de **Saint-Chamond (42400)** sur la date cible `2026-04-11` via **Open-Meteo**.

Règle d’alerte:

- créneaux `matin` (06:00–11:59) et `après-midi` (12:00–17:59), fuseau `Europe/Paris` ;
- avant `TARGET_DATE`, le job tourne toutes les heures et vérifie par anticipation la date cible (avant 12h: créneau matin, après 12h: créneau après-midi) ;
- si précipitation horaire `>= 1 mm`, envoi d’un message WhatsApp via API Meta (Cloud API) ;
- en cas d’échec WhatsApp, fallback immédiat par email via Resend ;
- après `TARGET_DATE`, le job retourne `skip_out_of_target_date` ;
- anti-duplication: clé d’idempotence interne par créneau (`meteo-alert/YYYY-MM-DD/{slot}`).

## Variables d’environnement

Copier `.env.example` vers `.env`, puis renseigner:

- `OPEN_METEO_BASE_URL` (optionnel, défaut: `https://api.open-meteo.com/v1/forecast`)
- `OPEN_METEO_MODEL` (optionnel, défaut: `auto`)
- `OPEN_METEO_TIMEOUT_SECONDS` (optionnel, défaut: `30`)
- `RESEND_API_KEY`
- `RESEND_FROM`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_BUSINESS_ACCOUNT_ID`
- `WHATSAPP_RECIPIENT_NUMBER` (format E.164, ex: `+33612345678`)
- `WHATSAPP_GRAPH_API_VERSION` (optionnel, défaut: `v25.0`)
- `WHATSAPP_TEMPLATE_NAME` (optionnel, défaut: `meteo_alerte_pluie_resume_v1`)
- `WHATSAPP_TEMPLATE_LANGUAGE` (optionnel, défaut: `fr_FR`)
- `WHATSAPP_TIMEOUT_SECONDS` (optionnel, défaut: `20`)

`ALERT_EMAIL_TO` est prérempli avec `vtndenis@gmail.com`.

Le template WhatsApp doit être créé et approuvé côté Meta avant l’envoi. Paramètres attendus dans le corps du template:

1. date (`YYYY-MM-DD`)
2. créneau (`matin` ou `après-midi`)
3. compte-rendu pluie (`HH:MM : X.XX mm; ...`)

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
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_BUSINESS_ACCOUNT_ID`

Variables d’environnement workflow utiles:

- `OPEN_METEO_BASE_URL`
- `OPEN_METEO_MODEL`
- `OPEN_METEO_TIMEOUT_SECONDS`
- `WHATSAPP_RECIPIENT_NUMBER`
- `WHATSAPP_GRAPH_API_VERSION`
- `WHATSAPP_TEMPLATE_NAME`
- `WHATSAPP_TEMPLATE_LANGUAGE`
- `WHATSAPP_TIMEOUT_SECONDS`

Le workflow est planifié toutes les heures (cron) et déclenchable manuellement.

## Tests

Lancer les tests avec `pytest`.

## Attribution des données météo

Les données météo proviennent de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0).
