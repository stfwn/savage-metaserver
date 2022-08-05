test:
	pytest --verbose

typecheck:
	mypy --namespace-packages .

serve:
	uvicorn metaserver.api:app --reload

