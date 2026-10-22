FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src ./src
COPY bin ./bin
# needed by the weekly training deployment
COPY data ./data

ENV PATH="/app/.venv/bin:$PATH"
# the processes in the container use the prefect server of the container,
# the UI (port 4201 mapped on 4200 of the host) calls the API through the host port
ENV PREFECT_API_URL=http://127.0.0.1:4201/api
ENV PREFECT_UI_API_URL=http://localhost:4200/api

# 8001: API, 4201: prefect UI
EXPOSE 8001 4201

CMD ["bash", "bin/run_services.sh"]
