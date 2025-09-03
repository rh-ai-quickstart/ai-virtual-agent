FROM python:3.11-slim

# Create a non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Set working directory
WORKDIR /app

# Install system dependencies needed for Oracle client
RUN apt-get update && apt-get install -y \
    libaio1 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client
RUN wget https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip \
    && unzip instantclient-basiclite-linuxx64.zip \
    && mv instantclient_* /opt/oracle \
    && rm instantclient-basiclite-linuxx64.zip \
    && echo /opt/oracle >> /etc/ld.so.conf.d/oracle-instantclient.conf \
    && ldconfig

# Set Oracle environment variables
ENV LD_LIBRARY_PATH=/opt/oracle:$LD_LIBRARY_PATH

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE 8003

# Run the MCP server
CMD ["python", "server.py"]