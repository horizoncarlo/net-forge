#!/bin/bash

export SITES_BASE_DIR=
export PUBLIC_HOST=

source .venv/bin/activate
#screen -d -m -S netforge sh -c "flask --app backend.py run -p 5000 --host=0.0.0.0 $@"
screen -d -m -S netforge sh -c "bash go-gunicorn.sh $@"
screen -r
