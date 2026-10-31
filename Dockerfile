FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 zittomind
USER zittomind
EXPOSE 8787
CMD ["zittomind", "serve", "--host", "0.0.0.0", "--config", "/config/zittomind.yaml"]
