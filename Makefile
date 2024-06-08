venv:
	python3 -mvenv venv
	venv/bin/pip install -r requirements.txt

test:
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest"

