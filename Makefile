.PHONY: run run-debug install clean help

help:
	@echo "Available commands:"
	@echo "  make install     - Install the package in editable mode"
	@echo "  make run         - Run notaider without debugging"
	@echo "  make run-debug   - Run notaider with debugpy enabled"
	@echo "  make clean       - Clean up Python cache files"

install:
	pip install -e .

run:
	python main.py

run-debug:
	python -c "import debugpy; debugpy.listen(('0.0.0.0', 5678)); print('🐛 Debug mode enabled - listening on 0.0.0.0:5678'); import runpy; runpy.run_path('main.py', run_name='__main__')"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
