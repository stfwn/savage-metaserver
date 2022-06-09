serve:
	uvicorn api:app --reload

test:
	pytest
