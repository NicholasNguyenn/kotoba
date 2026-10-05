FROM python:3.12-slim

# SudachiPy is pure Python; no MeCab build chain needed.
WORKDIR /app

COPY pyproject.toml README.md ./
COPY kotoba ./kotoba
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "kotoba.api:app", "--host", "0.0.0.0", "--port", "8000"]
