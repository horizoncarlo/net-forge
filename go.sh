#!/bin/bash
# Make sure you've setup a venv with `python -m venv .venv` then doing `source .venv/bin/activate`

export SITES_BASE_DIR=/var/www/html/
export PUBLIC_HOST=
export ENABLE_DEV_CORS=true
export ENABLE_FLASK_DEBUG=true

echo
echo ">>>> After startup open index.html in your browser locally as a file://, or use http-server or Nginx or similar"
echo

flask --app backend.py run --debug -p 5000 --host=0.0.0.0 $@
