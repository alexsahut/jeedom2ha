.PHONY: test test-unit test-integration test-cov

test:
	python3 -m pytest tests/ -v

test-unit:
	python3 -m pytest tests/unit/ -v

test-integration:
	python3 -m pytest tests/integration/ -v

test-cov:
	python3 -m pytest --cov=resources/daemon --cov-report=term-missing tests/
