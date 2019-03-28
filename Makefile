CWD=$(shell pwd)


build:
	docker-compose -f $(CWD)/docker-compose.yml build

test: build
	docker-compose \
		-f $(CWD)/docker-compose.yml \
		run --rm \
		--entrypoint "python /jalbot/test/main.py" \
		jalbot \
		--with-coverage \
		--cover-package=/jalbot/src

run:
	docker-compose \
	    -f $(CWD)/docker-compose.yml \
		run --rm \
		--entrypoint "python /jalbot/src/main.py" jalbot

stop:
	docker-compose down
