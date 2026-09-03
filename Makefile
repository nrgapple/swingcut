UV ?= uv
UV_ENV := UV_PYTHON_PREFERENCE=only-managed
PY := .venv/bin/python

.PHONY: setup lock dev configure-gemini-key doctor test lint format format-check build build-python build-swift build-photos-app test-swift check clean

setup:
	$(UV_ENV) $(UV) python install 3.12
	$(UV_ENV) $(UV) sync

lock:
	$(UV_ENV) $(UV) lock

dev: doctor
	$(PY) -m swingcut --help

configure-gemini-key:
	./scripts/configure-gemini-key.sh

doctor:
	$(PY) -m swingcut doctor

test:
	$(PY) -m pytest --cov=swingcut --cov-report=term-missing

lint:
	.venv/bin/ruff check .
	.venv/bin/mypy src
	xcrun swift-format lint --recursive --strict native/SwingcutPhotosBridge/Package.swift native/SwingcutPhotosBridge/Sources native/SwingcutPhotosBridge/Tests

format:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .
	xcrun swift-format format --recursive --in-place native/SwingcutPhotosBridge/Package.swift native/SwingcutPhotosBridge/Sources native/SwingcutPhotosBridge/Tests

format-check:
	.venv/bin/ruff format --check .
	xcrun swift-format lint --recursive --strict native/SwingcutPhotosBridge/Package.swift native/SwingcutPhotosBridge/Sources native/SwingcutPhotosBridge/Tests

build: build-python build-swift

build-python:
	$(PY) -m build

build-swift:
	swift build --package-path native/SwingcutPhotosBridge

build-photos-app:
	./scripts/build-photos-bridge-app.sh

test-swift: build-swift
	$$(swift build --package-path native/SwingcutPhotosBridge --show-bin-path)/swingcut-photos-bridge --version | grep -q '^swingcut-photos-bridge 0.1.0$$'

check: lint format-check test test-swift build

clean:
	$(PY) -c "import pathlib, shutil; [shutil.rmtree(path, ignore_errors=True) for path in map(pathlib.Path, ('build', 'dist', '.mypy_cache', '.pytest_cache', '.ruff_cache'))]; pathlib.Path('.coverage').unlink(missing_ok=True)"
	$(PY) -c "import pathlib, shutil; [shutil.rmtree(path) for root in ('src', 'tests') for path in pathlib.Path(root).rglob('__pycache__')]"
	swift package --package-path native/SwingcutPhotosBridge clean
