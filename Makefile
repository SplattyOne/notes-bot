LOCAL_COMPOSE_PATH=./docker-compose.local.yaml
LOCAL_ENV=--env-file ./.env.local

dev:
	./venv/bin/python ./src/main.py
local_up:
	docker-compose -f $(LOCAL_COMPOSE_PATH) $(LOCAL_ENV) up -d --build
local_down:
	docker-compose -f $(LOCAL_COMPOSE_PATH) $(LOCAL_ENV) down
build:
	docker build -t tomatto/notes-bot:1.0.0 . && docker push tomatto/notes-bot:1.0.0
