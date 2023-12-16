fmt:
	autoflake .
	isort .
	black .

lint:
	pylint filetransfer