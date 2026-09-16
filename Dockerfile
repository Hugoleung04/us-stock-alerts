FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY us_stock_alerts ./us_stock_alerts
COPY config.example.yaml ./
RUN pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "us_stock_alerts"]
CMD ["--config", "config.example.yaml", "--no-notify"]
