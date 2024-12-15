PYTEST_COV_ARGS =

FORCE: ;

create-venv:
	python3.11 -mvenv venv

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

requirements.txt: deps-top.txt recreate-venv
	venv/bin/pip install -r deps-top.txt
	echo '# GENERATED: run make requirements.txt to recreate lock file' > requirements.txt
	venv/bin/pipdeptree --freeze >> requirements.txt

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
	venv/bin/pybabel extract -F babel.cfg -k lazy_gettext -k hardcode_text -o messages.pot app
	venv/bin/pybabel update -i messages.pot -d app/translations

babel-update-mo: babel-update-po
	venv/bin/pybabel compile -d app/translations

babel-translate-po:
	venv/bin/python app/scripts/fill_zh_translations.py
	venv/bin/python app/scripts/fill_en_translations.py
