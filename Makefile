PYTEST_COV_ARGS = --cov=app --cov-report=term --cov-report=xml:cov.xml

FORCE: ;

create-venv:
	python3.10 -mvenv venv

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

test_all_cov:
	venv/bin/pytest --html=report.html --self-contained-html $(PYTEST_COV_ARGS)

test_all:
	venv/bin/pytest --html=report.html --self-contained-html

test_all_parallel:
	venv/bin/pytest -n 8

test_single:
	venv/bin/pytest tests/base/test_not_exist_error.py

test_logging:
	#--capture=no  
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_it_runs.py"
	# @bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_it_runs.py"
