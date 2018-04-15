CPUS ?= $(shell sysctl -n hw.ncpu || echo 1)
MAKEFLAGS += --jobs=$(CPUS)

develop: setup-git install-requirements

upgrade: install-requirements
	createdb -E utf-8 pipet || true
	pipet db upgrade

setup-git:
	pip install pre-commit==1.4.3
	pre-commit install
	git config branch.autosetuprebase always
	git config --bool flake8.strict true
	cd .git/hooks && ln -sf ../../hooks/* ./

install-requirements: install-python-requirements install-js-requirements

install-python-requirements:
	pip install "setuptools>=17.0"
	pip install "pip>=9.0.0,<10.0.0"
	pip install -e .

install-js-requirements:
	yarn install

test:
	py.test tests

reset-db:
	$(MAKE) drop-db
	$(MAKE) create-db
	pipet db upgrade

drop-db:
	dropdb --if-exists pipet

create-db:
	createdb -E utf-8 pipet

build-docker-image:
	docker build -t pipet .

run-docker-image:
	docker rm pipet || exit 0
	docker run  -d -p 8080:8080/tcp -v ~/.pipet:/workspace --name pipet pipet
