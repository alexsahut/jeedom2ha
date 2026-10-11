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
# --sha is mandatory (CC-56 guardrail): always the current HEAD, computed
# here so an accidental bare invocation of the script itself still refuses.
deploy:
	./scripts/deploy-to-box.sh --sha "$$(git rev-parse HEAD)"

deploy-dry:
	./scripts/deploy-to-box.sh --sha "$$(git rev-parse HEAD)" --dry-run

deploy-restart:
	./scripts/deploy-to-box.sh --sha "$$(git rev-parse HEAD)" --restart-daemon

deploy-clean:
	./scripts/deploy-to-box.sh --sha "$$(git rev-parse HEAD)" --cleanup-discovery
