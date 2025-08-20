#!/usr/bin/env bash
set -euo pipefail

# Simple bootstrapper for Oracle Free 23ai with SH sample schema on Apple Silicon
# - Starts the container (arm64) with larger SHM
# - Waits for readiness
# - Downloads Oracle sample schemas if missing
# - Mounts sales_history into the container
# - Creates application user (mcp)
# - Installs SH schema non-interactively

CONTAINER_NAME=${CONTAINER_NAME:-oracle-xe}
IMAGE=${IMAGE:-gvenzl/oracle-free:23-slim}
PLATFORM=${PLATFORM:-linux/arm64}
SHM_SIZE=${SHM_SIZE:-2g}
ORACLE_PASSWORD=${ORACLE_PASSWORD:-Passw0rd}
HOST_PORT_1521=${HOST_PORT_1521:-1521}
HOST_PORT_5500=${HOST_PORT_5500:-5500}

# Location for sample schemas on host
ROOT_DIR=$(cd "$(dirname "$0")"/../.. && pwd)
SCHEMAS_ROOT=${SCHEMAS_ROOT:-"$ROOT_DIR/../db-sample-schemas-main"}
SALES_DIR="$SCHEMAS_ROOT/sales_history"

echo "[INFO] Using container: $CONTAINER_NAME"
echo "[INFO] Image: $IMAGE"
echo "[INFO] Platform: $PLATFORM  SHM: $SHM_SIZE"
echo "[INFO] Host ports: 1521->$HOST_PORT_1521  5500->$HOST_PORT_5500"

# Ensure sample schemas are present
if [[ ! -d "$SALES_DIR" ]]; then
  echo "[INFO] Downloading Oracle sample schemas..."
  workdir=$(pwd)
  cd "$ROOT_DIR/.."
  curl -L -o db-sample-schemas.zip \
    https://github.com/oracle-samples/db-sample-schemas/archive/refs/heads/main.zip
  unzip -q -o db-sample-schemas.zip
  rm -f db-sample-schemas.zip
  cd "$SALES_DIR"
  # Replace placeholder with absolute path in SH scripts
  perl -p -i.bak -e 's#__SUB__CWD__#'"$SALES_DIR"'#g' sh_*.sql || true
  cd "$workdir"
else
  echo "[INFO] Found sample schemas at $SALES_DIR"
  (cd "$SALES_DIR" && perl -p -i.bak -e 's#__SUB__CWD__#'"$SALES_DIR"'#g' sh_*.sql || true)
fi

echo "[INFO] (Re)starting container..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d --name "$CONTAINER_NAME" \
  --platform="$PLATFORM" \
  --shm-size="$SHM_SIZE" \
  -p "$HOST_PORT_1521":1521 -p "$HOST_PORT_5500":5500 \
  -e ORACLE_PASSWORD="$ORACLE_PASSWORD" \
  -v "$SALES_DIR":/opt/schemas/sales_history:ro \
  "$IMAGE"

echo "[INFO] Waiting for database readiness..."
READY_MARKER="DATABASE IS READY TO USE!"
start_ts=$(date +%s)
timeout_sec=600
while true; do
  if docker logs "$CONTAINER_NAME" 2>&1 | grep -q "$READY_MARKER"; then
    echo "[INFO] Database is ready."
    break
  fi
  now=$(date +%s)
  if (( now - start_ts > timeout_sec )); then
    echo "[ERROR] Timed out waiting for database readiness." >&2
    exit 1
  fi
  sleep 3
done

echo "[INFO] Creating application user (mcp) if not exists..."
docker exec -i "$CONTAINER_NAME" bash -lc "sqlplus -s system/$ORACLE_PASSWORD@localhost/FREEPDB1 <<'SQL'
WHENEVER SQLERROR EXIT SQL.SQLCODE
DECLARE
  v_count NUMBER := 0;
BEGIN
  SELECT COUNT(*) INTO v_count FROM dba_users WHERE username = 'MCP';
  IF v_count = 0 THEN
    EXECUTE IMMEDIATE 'CREATE USER mcp IDENTIFIED BY mcp_password QUOTA UNLIMITED ON USERS';
    EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE TO mcp';
  END IF;
END;
/
EXIT
SQL"

echo "[INFO] Installing SH sample schema (non-interactive)..."
docker exec -i "$CONTAINER_NAME" bash -lc "cd /tmp && printf 'sh\nUSERS\nTEMP\n$ORACLE_PASSWORD\n/opt/schemas/sales_history\n/tmp\nv3\nlocalhost/FREEPDB1\n' | sqlplus -s system/$ORACLE_PASSWORD@localhost/FREEPDB1 @/opt/schemas/sales_history/sh_install.sql"

echo "[INFO] Verifying SH schema..."
docker exec -i "$CONTAINER_NAME" bash -lc "echo 'select count(*) as CUSTOMERS from sh.customers; exit' | sqlplus -s sh/sh@localhost/FREEPDB1"

echo "[SUCCESS] Oracle container is running and SH schema installed."
