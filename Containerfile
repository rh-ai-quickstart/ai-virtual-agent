# ---------- Frontend Build ----------
FROM registry.access.redhat.com/ubi9/nodejs-22 AS frontend-builder

USER root

WORKDIR /app/frontend

# Copy only package files first to leverage Docker cache
COPY frontend/package*.json ./

RUN npm install --debug

# Now copy the rest of the frontend code
COPY frontend/ ./

# Set node memory limit if needed
ENV NODE_OPTIONS=--max-old-space-size=512

# Run linting before build
RUN npm run lint:fix
RUN npm run format:check
RUN npm run build


# ---------- Backend Build ----------
FROM registry.access.redhat.com/ubi9/python-311:latest

USER root
# Set working directory
WORKDIR /app

RUN dnf install -y nmap-ncat && dnf clean all

# Copy backend and install dependencies
COPY backend/ ./backend/
COPY frontend/src/assets/ ./backend/public/assets
COPY entrypoint.sh .
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend to backend's static files
COPY --from=frontend-builder /app/frontend/dist ./backend/public/

# Create templates directory with proper permissions for user 1001
RUN mkdir -p /app/templates && chown -R 1001:1001 /app/templates

# Copy templates directory
COPY templates/ ./templates/

USER 1001
# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["./entrypoint.sh"]
