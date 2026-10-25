FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "fraudshield.api:app", "--host", "0.0.0.0", "--port", "8000"]