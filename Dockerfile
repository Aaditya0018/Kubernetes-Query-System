# Use a Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
# Note: You should have a requirements.txt with: fastmcp, fastapi, uvicorn, kubernetes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Use the mcp_server.py as the entry point
# This runs your FastMCP application, which exposes the MCP endpoints
CMD ["python", "mcp_server.py"]