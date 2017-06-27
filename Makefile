bootstrap:
	createdb pipet

init:
	python -c "from pipet import create_all; create_all()"

reset-db:
	python -c "from pipet import create_all, drop_all; drop_all(); create_all()"

devserver:
	export FLASK_DEBUG=true
	flask run

backfill-zendesk:
	python -c "from pipet.sources.zendesk import backfill; backfill()"
