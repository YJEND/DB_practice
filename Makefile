# ------------------------------------------------------------------
# DB 심화 실습 환경 명령 모음.   `make` 로 목록 확인
# .env 의 포트/계정을 읽어 사용합니다 (없으면 lab/lab, 5432, 6379).
# ------------------------------------------------------------------
-include .env
export

SHELL := /bin/bash
.DEFAULT_GOAL := help

POSTGRES_USER ?= lab
POSTGRES_PASSWORD ?= lab
POSTGRES_DB ?= lab
MYSQL_USER ?= lab
MYSQL_PASSWORD ?= lab
MYSQL_DATABASE ?= lab

COMPOSE     := docker compose
COMPOSE_ALL := docker compose --profile mysql
# 대화형 psql (터미널에 붙음)
PSQL   := $(COMPOSE) exec postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)
# 파일/파이프 입력용 psql (-T: TTY 없이, 에러 나면 즉시 중단)
PSQL_T := $(COMPOSE) exec -T postgres psql -v ON_ERROR_STOP=1 -U $(POSTGRES_USER) -d $(POSTGRES_DB)
MYSQL  := $(COMPOSE_ALL) exec mysql mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE)

.PHONY: help up up-mysql down reset restart-pg ps logs status \
	    psql psql-a psql-b redis-cli mysql sql \
	    seed-small seed-large _seed seed-mysql verify venv

help: ## 명령 목록
	@echo ""
	@echo "  DB 실습 환경  (PostgreSQL $(POSTGRES_PORT) / Redis $(REDIS_PORT) / MySQL $(MYSQL_PORT))"
	@echo ""
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  트랜잭션/락 실습: 터미널 두 개를 열고 각각 'make psql-a', 'make psql-b' 실행"
	@echo ""

# ---------------------------------------------------------------- 컨테이너
up: ## postgres + redis 기동 (healthy 될 때까지 대기)
	$(COMPOSE) up -d --wait
	@$(MAKE) --no-print-directory status

up-mysql: ## MySQL(InnoDB) 비교용 컨테이너까지 기동
	$(COMPOSE_ALL) up -d --wait

down: ## 컨테이너 중지 (데이터 볼륨은 유지)
	$(COMPOSE_ALL) down

reset: ## 컨테이너 + 볼륨(데이터) 전부 삭제. 확인 프롬프트 있음
	@echo ""
	@echo "  !! 모든 컨테이너와 named volume(pg_data, redis_data, mysql_data)을 삭제합니다."
	@echo "  !! 시드 데이터, pg_stat_statements 누적치, Redis 키가 모두 사라집니다."
	@echo ""
	@read -p "  정말 삭제할까요? [y/N] " ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
	    $(COMPOSE_ALL) down -v --remove-orphans && echo "  삭제 완료. 'make up' 으로 다시 시작하세요."; \
	else echo "  취소했습니다."; fi

restart-pg: ## postgresql.conf 변경 후 PostgreSQL 만 재시작
	$(COMPOSE) restart postgres
	@$(COMPOSE) up -d --wait postgres
	@$(PSQL_T) -c "SHOW shared_preload_libraries;"

ps: ## 컨테이너 상태
	$(COMPOSE_ALL) ps

logs: ## PostgreSQL 로그 follow (auto_explain, lock wait, autovacuum 로그가 여기 찍힘)
	$(COMPOSE) logs -f --tail=100 postgres

status: ## 헬스체크 + 확장(vector, pg_stat_statements) + Redis PING 확인
	@$(COMPOSE_ALL) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo "--- PostgreSQL ---"
	@$(PSQL_T) -Atc "SELECT version();"
	@$(PSQL_T) -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector','pg_stat_statements','pgstattuple','pg_buffercache') ORDER BY 1;"
	@$(PSQL_T) -Atc "SELECT 'shared_preload_libraries = ' || current_setting('shared_preload_libraries');"
	@$(PSQL_T) -Atc "SELECT 'pg_stat_statements rows = ' || count(*) FROM pg_stat_statements;"
	@echo "--- Redis ---"
	@$(COMPOSE) exec redis redis-cli ping

# ---------------------------------------------------------------- 접속
psql: ## psql 접속
	$(PSQL)

psql-a: ## 세션 A (프롬프트 [A]) — 트랜잭션/락 실습용 1번 터미널
	$(COMPOSE) exec -e PGAPPNAME=session_A postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
	    -v PROMPT1='[A] %/%R%# ' -v PROMPT2='[A] %/%R%# '

psql-b: ## 세션 B (프롬프트 [B]) — 트랜잭션/락 실습용 2번 터미널
	$(COMPOSE) exec -e PGAPPNAME=session_B postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) \
	    -v PROMPT1='[B] %/%R%# ' -v PROMPT2='[B] %/%R%# '

redis-cli: ## redis-cli 접속
	$(COMPOSE) exec redis redis-cli

mysql: ## mysql 클라이언트 접속 (up-mysql 이후)
	$(MYSQL)

sql: ## SQL 파일 실행: make sql FILE=labs/06-pgvector/setup.sql [VARS="-v n=1000"]
	@test -n "$(FILE)" || (echo "사용법: make sql FILE=path/to/file.sql"; exit 1)
	$(PSQL_T) $(VARS) < $(FILE)

# ---------------------------------------------------------------- 시드
seed-small: ## 시드 small: users 10만 / orders 100만 / items 약 225만 (약 10초, ~330MB)
	@$(MAKE) --no-print-directory _seed SCALE=small
	@$(MAKE) --no-print-directory verify

seed-large: ## 시드 large: users 100만 / orders 1,000만 / items 약 2,200만 (확인 프롬프트)
	@echo ""
	@echo "  large 모드는 users 100만, orders 1,000만, order_items 약 2,200만 행을 만듭니다."
	@echo "  예상 디스크: 약 3.5~5GB (WAL 포함)   예상 시간: 2~5분 (Apple Silicon 기준, small 이 6초 걸린 머신 기준 추정)"
	@echo "  기존 users/products/orders/order_items 테이블은 DROP 후 다시 만듭니다."
	@echo "  Docker Desktop 의 디스크 제한(Settings > Resources)이 충분한지 먼저 확인하세요."
	@echo ""
	@read -p "  진행할까요? [y/N] " ans; \
	if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
	    $(MAKE) --no-print-directory _seed SCALE=large && $(MAKE) --no-print-directory verify; \
	else echo "  취소했습니다."; fi

_seed:
	@echo ">>> seed scale=$(SCALE)  (시작: $$(date +%H:%M:%S))"
	@cat seed/00-schema.sql seed/10-seed.sql | $(PSQL_T) -v scale=$(SCALE)
	@echo ">>> seed 완료 (종료: $$(date +%H:%M:%S))"

seed-mysql: ## MySQL 에 small 규모 시드 (up-mysql 이후, 비교 실습용)
	@echo ">>> MySQL seed (small)"
	@$(COMPOSE_ALL) exec -T mysql mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE) < seed/mysql/seed_small.sql
	@$(COMPOSE_ALL) exec -T mysql mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE) < seed/mysql/verify.sql

verify: ## 테이블별 행 수 / 크기 / 분포 확인
	@$(PSQL_T) < seed/verify.sql

# ---------------------------------------------------------------- 도구
venv: ## Python 가상환경 생성 + 측정 도구 의존성 설치
	python3 -m venv .venv
	.venv/bin/pip install -q --upgrade pip
	.venv/bin/pip install -q -r requirements.txt
	@echo "완료: source .venv/bin/activate  또는  .venv/bin/python tools/measure.py ..."
