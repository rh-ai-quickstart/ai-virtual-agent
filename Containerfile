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

RUN npm run build


# ---------- Backend Build ----------
FROM registry.redhat.io/ubi9/python-311@sha256:fc669a67a0ef9016c3376b2851050580b3519affd5ec645d629fd52d2a8b8e4a

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


USER 1001
# Expose FastAPI port
EXPOSE 8000

# Start FastAPI server
CMD ["./entrypoint.sh"]
