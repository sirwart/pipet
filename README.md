# Pipet

SQL for APIs

## To run

1. Set the environment variables found in `.sample_env`

2. `make develop`

3. Run the application either with `flask run` or Docker.

4. `watchmedo shell-command --patterns="*.py" --recursive --command='pkill -f celery; celery -A pipet.celery worker'`
