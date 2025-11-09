FROM python:3.11-slim
WORKDIR /app
COPY mock/bank_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mock/bank_server/main.py .
# Copy bank_stub data
COPY bank_stub /bank_stub
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
