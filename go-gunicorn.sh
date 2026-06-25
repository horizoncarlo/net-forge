# Single worker to match what we did with Flask, and also to keep any in-memory data in sync
# Put access and error logs to stdout, so that pm2 or screen or whatever will show it
gunicorn --access-logfile - --error-logfile - -b 0.0.0.0:5000 backend:app $@
