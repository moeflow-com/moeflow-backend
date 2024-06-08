venv:
	python3 -mvenv venv
	venv/bin/pip install -r requirements.txt

format:
	venv/bin/ruff format

test:
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest"

test_smoketest:
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=no tests/base/test_regex.py"
