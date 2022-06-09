serve:
	uvicorn metaserver.api:app --reload

test:
	pytest
