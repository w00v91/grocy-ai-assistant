install:
	pip install -r requirements.txt

run:
	python -m grocy_ai_assistant.api.main

test:
	pytest

lint:
	ruff check .

format:
	black .