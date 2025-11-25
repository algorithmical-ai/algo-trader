export PYTHONPATH=$(PWD)/app

.PHONY: setup test lint format clean

YELLOW := \033[1;33m
NC     := \033[0m

setup:
	@echo "$(YELLOW)Creating fresh conda env 'algo-trader' (Python 3.11 + TA-Lib 0.6.4)...$(NC)"
	conda env remove -n algo-trader -y 2>/dev/null || true
	conda env create -f environment.yml
	@echo "$(YELLOW)Pip installing deps (alpaca-py latest)...$(NC)"
	conda run -n algo-trader pip install -r requirements.txt -r requirements-dev.txt
	@echo "$(YELLOW)SUCCESS! Activate: conda activate algo-trader$(NC)"

test:
	@echo "$(YELLOW)Running tests...$(NC)"
	conda run -n algo-trader pytest app/tests/ -v --cov=algo_trader --cov-report=html

format:
	@echo "$(YELLOW)Formatting code...$(NC)"
	conda run -n algo-trader black algo_trader/ app/tests/
	conda run -n algo-trader isort algo_trader/ app/tests/

lint:
	@echo "$(YELLOW)Running pylint...$(NC)"
	conda run -n algo-trader pylint algo_trader/ app/tests/ --score=y

clean:
	@echo "$(YELLOW)Cleaning...$(NC)"
	conda env remove -n algo-trader -y 2>/dev/null || true
	-rm -rf logs/ __pycache__/ */__pycache__/ .pytest_cache/ htmlcov/ environment.yml
