FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# MCP server kjører via stdio
CMD ["python", "-m", "mcp.server.fastmcp.run", "server:mcp"]
