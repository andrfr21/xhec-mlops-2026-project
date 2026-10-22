#!/bin/bash

prefect server start --host 0.0.0.0 --port 4201 &
uvicorn src.web_service.main:app --host 0.0.0.0 --port 8001
