
docker exec devanalysis114-backend curl -s http://127.0.0.1:8000/api/marketplace/projects | python -m json.tool | Select-Object -First 150
