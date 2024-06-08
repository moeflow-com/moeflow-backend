venv:
	python3 -mvenv venv
	venv/bin/pip install -r requirements.txt

format:
	venv/bin/ruff format 

test:
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest"

test_smoketest:
	#--capture=no  
	# WTF: setting level to above WARNING not working?
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_it_runs.py"
