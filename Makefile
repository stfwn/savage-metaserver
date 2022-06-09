test:
	pytest --verbose

serve:
	uvicorn metaserver.api:app --reload

