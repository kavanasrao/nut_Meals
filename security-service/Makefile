.PHONY: dev test test-up test-down migrate lint format build

dev:
	docker compose up --build

test-up:
	docker compose -f docker-compose.test.yml up -d
	sleep 3

test-down:
	docker compose -f docker-compose.test.yml down -v

test: test-up
	TEST_DATABASE_URL=postgresql+asyncpg://nutmeals:nutmeals@localhost:5433/security_db_test \
	SECURITY_REDIS_URL=redis://localhost:6380/0 \
	SECURITY_JWT_SECRET=local-test-secret \
	alembic upgrade head && pytest
	$(MAKE) test-down

migrate:
	alembic upgrade head

lint:
	ruff check . && black --check .

format:
	ruff check --fix . && black .

build:
	docker build --target runtime -t nutmeals/security-service:local .
