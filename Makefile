# Makefile – FINAL VERSION (works on M1/M2 + app/algo_trader layout)
.PHONY: setup test lint format clean

YELLOW := \033[1;33m
NC     := \033[0m

# THIS LINE IS THE KEY – points to the directory that contains the algo_trader package
export PYTHONPATH=$(PWD)/app

test:
	@echo "$(YELLOW)Running tests...$(NC)"
	conda run -n algo-trader pytest app/tests/ -v --cov=algo_trader --cov-report=html

lint:
	@echo "$(YELLOW)Running pylint...$(NC)"
	conda run -n algo-trader pylint app/ app/tests/ --score=y

format:
	@echo "$(YELLOW)Formatting code...$(NC)"
	conda run -n algo-trader black app/ app/tests/
	conda run -n algo-trader isort app/ app/tests/

setup:
	@echo "$(YELLOW)Environment already created – just run tests!$(NC)"

clean:
	@echo "$(YELLOW)Cleaning...$(NC)"
	-conda env remove -n algo-trader -y
	-rm -rf logs/ __pycache__/ */__pycache__ .pytest_cache/ htmlcov/