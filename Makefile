init:
	python -c "from app import create_all; create_all()"

reset-db:
	python -c "from app import create_all, drop_all; drop_all(); create_all()"

devserver:
	export FLASK_DEBUG=true
	flask run
