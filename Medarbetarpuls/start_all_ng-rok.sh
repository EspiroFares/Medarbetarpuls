#!/bin/bash

# Also need to run ngrok config visit website

# Kill old processes (optional safety)
pkill -f runserver
pkill -f ngrok
pkill -f 'celery'

# Start Django temporarily so ngrok has something to forward
python manage.py runserver 0.0.0.0:8000 &

# Wait a bit to ensure Django starts
sleep 3

# Start ngrok in background
ngrok http 8000 &

# Wait for ngrok to initialize
sleep 3

# Get ngrok public URL from its local API
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[a-z0-9\-]*\.ngrok[-a-z]*\.app' | head -n 1)
NGROK_HOST=$(echo "$NGROK_URL" | sed 's|https://||')

echo "Ngrok public URL: $NGROK_URL"
echo "Ngrok host to allow: $NGROK_HOST"

# Kill temporary Django instance
pkill -f runserver

# Export for use in Django settings
export NGROK_HOST=$NGROK_HOST

# Start Django again with correct host
python manage.py runserver 0.0.0.0:8000 &

# Start Celery beat
celery -A Medarbetarpuls worker -l info