init:
	source .env
	python -c "from app import create_all; create_all()"

reset-db:
	source .env
	python -c "from app import create_all, drop_all; drop_all(); create_all()"

devserver:
	export FLASK_DEBUG=true
	source .env
	flask run
