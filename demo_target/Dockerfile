FROM python:3.11-slim

WORKDIR /app

COPY demo_target/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY demo_target/app.py .

# No volumes mounted, no destructive tool logic exists in app.py,
# runs as non-root, exposes only the chat port.
RUN useradd -m sandboxuser
USER sandboxuser

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
