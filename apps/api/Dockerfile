FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY apps ./apps
COPY packages ./packages
COPY data/manifests ./data/manifests
COPY reports ./reports
COPY data/processed/cycles.parquet ./data/processed/cycles.parquet
RUN pip install --no-cache-dir .
USER 10001
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

