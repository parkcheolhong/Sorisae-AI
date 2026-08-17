# FILE-ID: FILE-DOCKERFILE
# SECTION-ID: SECTION-DOCKERFILE-MAIN
# FEATURE-ID: FEATURE-DOCKERFILE-RUNTIME
# CHUNK-ID: CHUNK-DOCKERFILE-001

FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements.delivery.lock.txt
CMD ["python", "-m", "uvicorn", "app.main:create_application", "--factory", "--host", "0.0.0.0", "--port", "8000"]
