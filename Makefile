LOCAL_COMPOSE_PATH=./docker-compose.local.yaml
LOCAL_ENV=--env-file ./.env.local
TIMESTAMP_NOW=$(shell echo $$(date +"%Y%m%d%H%M%S"))

dev:
	./venv/bin/python ./src/main.py
local_up:
	docker-compose -f $(LOCAL_COMPOSE_PATH) $(LOCAL_ENV) up -d --build
local_down:
	docker-compose -f $(LOCAL_COMPOSE_PATH) $(LOCAL_ENV) down
build:
	docker build -t tomatto/notes-bot:1.0.$(TIMESTAMP_NOW) . --platform="linux/amd64" && \
	docker push tomatto/notes-bot:1.0.$(TIMESTAMP_NOW) && \
	docker tag tomatto/notes-bot:1.0.$(TIMESTAMP_NOW) tomatto/notes-bot:latest && \
	docker push tomatto/notes-bot:latest

