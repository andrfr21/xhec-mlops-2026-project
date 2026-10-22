FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY bin ./bin

ENV PATH="/app/.venv/bin:$PATH"

# 8001: API, 4201: prefect UI
EXPOSE 8001 4201

CMD ["bash", "bin/run_services.sh"]
