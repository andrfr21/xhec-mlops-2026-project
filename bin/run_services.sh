#!/bin/bash

prefect server start --host 0.0.0.0 --port 4201 &

# in the background: serve the weekly training deployment once the prefect server answers
(
    until python -c "import urllib.request; urllib.request.urlopen('$PREFECT_API_URL/health')" 2>/dev/null; do
        sleep 1
    done
    python src/modelling/deployment.py
) &

# the API does not wait for prefect
# exec: uvicorn replaces bash, so it gets the signal of docker stop
exec uvicorn src.web_service.main:app --host 0.0.0.0 --port 8001
