.PHONY: install test dev-api dev-web build

install:
	pip install -r requirements.txt
	cd apps/web && npm install

test:
	PYTHONPATH=apps/api:libs/rag/src .venv/bin/python -m pytest apps/api/tests libs/rag/tests -q

dev-api:
	PYTHONPATH=apps/api:libs/rag/src .venv/bin/python -m uvicorn server:app --app-dir apps/api --reload --port 8000

dev-web:
	cd apps/web && npm run dev

build:
	cd apps/web && npm run build
