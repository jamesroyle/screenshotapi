#!/bin/bash

playwright install --with-deps

exec uvicorn main:app --host 0.0.0.0 --port 10000