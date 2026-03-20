.PHONY: test test-unit test-integration test-cov \
        deploy deploy-dry deploy-restart deploy-clean

test:
	python3 -m pytest tests/ -v

test-unit:
	python3 -m pytest tests/unit/ -v

test-integration:
	python3 -m pytest tests/integration/ -v

test-cov:
	python3 -m pytest --cov=resources/daemon --cov-report=term-missing tests/

# DEV/TEST ONLY — deploy to local test box (not a release procedure)
deploy:
	./scripts/deploy-to-box.sh

deploy-dry:
	./scripts/deploy-to-box.sh --dry-run

deploy-restart:
	./scripts/deploy-to-box.sh --restart-daemon

deploy-clean:
	./scripts/deploy-to-box.sh --cleanup-discovery
