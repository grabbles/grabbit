dev-install:
	pip install -r requirement.txt
	pip install -e .

test: 
	py.test --cov=grabbids --pyargs grabbids 

