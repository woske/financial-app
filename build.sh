#!/usr/bin/env bash
# Build script for Render

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput
