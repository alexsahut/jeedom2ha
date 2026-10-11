.PHONY: test test-unit test-integration test-cov \
        check-sha deploy deploy-dry deploy-restart deploy-clean

test:
	python3 -m pytest tests/ -v

test-unit:
	python3 -m pytest tests/unit/ -v

test-integration:
	python3 -m pytest tests/integration/ -v

test-cov:
	python3 -m pytest --cov=resources/daemon --cov-report=term-missing tests/

# DEV/TEST ONLY — deploy to local test box (not a release procedure)
# --sha is mandatory (CC-56 guardrail). SHA must be passed explicitly
# (make deploy SHA=<sha>) rather than computed automatically, so a bare
# `make deploy` — e.g. quoted in a prompt — refuses instead of deploying.
check-sha:
	@test -n "$(SHA)" || { echo "Error: SHA is required. Usage: make deploy SHA=\$$(git rev-parse HEAD)" >&2; exit 1; }

deploy: check-sha
	./scripts/deploy-to-box.sh --sha "$(SHA)"

deploy-dry: check-sha
	./scripts/deploy-to-box.sh --sha "$(SHA)" --dry-run

deploy-restart: check-sha
	./scripts/deploy-to-box.sh --sha "$(SHA)" --restart-daemon

deploy-clean: check-sha
	./scripts/deploy-to-box.sh --sha "$(SHA)" --cleanup-discovery
