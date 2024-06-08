venv:
	python3 -mvenv venv
	venv/bin/pip install -r requirements.txt

format:
	venv/bin/ruff format 

test:
	@./pytest --html=report.html --self-contained-html

test_p:
	@./pytest -n 8

test_single:
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_not_exist_error.py"

test_logging:
	#--capture=no  
	# WTF: setting level to above WARNING not working?
	@bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_it_runs.py"
	# @bash -c "set -uexo allexport && source .env.test && exec venv/bin/pytest --capture=sys --log-cli-level=DEBUG tests/base/test_it_runs.py"
