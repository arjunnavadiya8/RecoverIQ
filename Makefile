PYTHON ?= python

.PHONY: setup data demo-data warehouse train causal test app api lint clean

setup:
	$(PYTHON) -m pip install -e ".[dev]"

data:
	$(PYTHON) -m recoveriq.cli download
	$(PYTHON) -m recoveriq.cli ingest
	dbt build --profiles-dir .

demo-data:
	$(PYTHON) -m recoveriq.cli demo-data --force
	$(PYTHON) -m recoveriq.cli ingest
	dbt build --profiles-dir .

warehouse:
	$(PYTHON) -m recoveriq.cli ingest
	dbt build --profiles-dir .

train:
	$(PYTHON) -m recoveriq.cli train

causal:
	$(PYTHON) -m recoveriq.cli causal

test:
	pytest --cov=recoveriq --cov-report=term-missing

lint:
	ruff check src tests app.py

app:
	streamlit run app.py

api:
	uvicorn recoveriq.api:app --host 0.0.0.0 --port 8000

clean:
	$(PYTHON) -m recoveriq.cli clean-derived

