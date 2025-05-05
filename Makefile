PYTEST_COV_ARGS =

BIN_PREFIX ?= venv/bin

PYTHON_BIN = python3.11

FORCE: ;

create-venv:
	$(PYTHON_BIN) -mvenv venv

deps:
	venv/bin/pip install -r requirements.txt

remove-venv: FORCE
	rm -rf venv

recreate-venv: remove-venv create-venv

lint:
	venv/bin/ruff check

lint-fix:
	venv/bin/ruff --fix

format:
	venv/bin/ruff format

requirements.txt: deps-top.txt
	rm -rf venv-rebuild-deps
	$(PYTHON_BIN) -mvenv venv-rebuild-deps
	venv-rebuild-deps/bin/pip install -r deps-top.txt
	echo '# GENERATED: run make requirements.txt to recreate lock file' > requirements.txt
	venv-rebuild-deps/bin/pipdeptree --freeze >> requirements.txt
	rm -rf venv-rebuild-deps

test: test_all

test_all:
	venv/bin/pytest

test_all_parallel:
	# TODO: fix this
	venv/bin/pytest -n 8

test_single:
	venv/bin/pytest tests/api/test_file_api.py

test_logging:
	#--capture=no
	venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_logging.py

babel-update-po:
	$(BIN_PREFIX)/pybabel extract -F babel.cfg -k lazy_gettext -k hardcode_text -o messages.pot app
	$(BIN_PREFIX)/pybabel update -i messages.pot -d app/translations

babel-update-mo: babel-update-po
	$(BIN_PREFIX)/pybabel compile -d app/translations

babel-translate-po:
	venv/bin/python app/scripts/fill_zh_translations.py
	venv/bin/python app/scripts/fill_en_translations.py
