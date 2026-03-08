
#!/usr/bin/with-contenv bashio

echo "Starting Grocy AI Assistant"
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
