FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopier klient-kode
COPY client.py .

# Opprett directory for MCP server
RUN mkdir -p /mcp-server

EXPOSE 8001

CMD ["python", "client.py"]
