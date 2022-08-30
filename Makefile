test:
	pytest --verbose

typecheck:
	mypy --namespace-packages .

serve:
	uvicorn metaserver.api:app --reload

database-backup:
	aws s3 cp metaserver.db s3://savage-metaserver/database-backup/$$(date --utc +%Y-%m-%dT%H:%M).db

deploy:
	docker compose up -d
