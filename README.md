# Pipet

For piping little data into Postgres.

## To run

Requires environment variable:

- `ZENDESK_EMAIL`
- `ZENDESK_API_KEY`
- `ZENDESK_SUBDOMAIN`

In development, pass `DEVELOPMENT_DOMAIN` to use ngrok. Zendesk doesn't accept localhost target urls.

`export FLASK_APP=app.py flask run`
