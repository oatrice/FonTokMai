FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y fonts-liberation fonts-thai-tlwg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the FastAPI application using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
