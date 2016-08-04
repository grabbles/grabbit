dev-install:
	pip install -r requirement.txt
	pip install -e .

test: 
	py.test --cov=grabbit --pyargs grabbit 

