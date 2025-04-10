#!/usr/bin/env bash
set -o errexit  # stop if any command fails

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
