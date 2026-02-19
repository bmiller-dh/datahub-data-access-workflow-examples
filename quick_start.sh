#!/usr/bin/env bash
# Quick start: stand up the mock server and all four action pipelines.
# Run from the repo root. Requires .env with DATAHUB_URL and DATAHUB_TOKEN.
# Optional: Docker for the mock server; Python venv and pip install -e . for pipelines.

set -e
cd "$(dirname "$0")"

# Load .env
if [ ! -f .env ]; then
  echo "Error: .env not found. Copy .env.example to .env and set DATAHUB_URL and DATAHUB_TOKEN." >&2
  exit 1
fi
set -a && source .env && set +a
if [ -z "$DATAHUB_URL" ] || [ -z "$DATAHUB_TOKEN" ]; then
  echo "Error: DATAHUB_URL and DATAHUB_TOKEN must be set in .env." >&2
  exit 1
fi

# Activate venv if present
if [ -d venv ]; then
  source venv/bin/activate
fi

# Ensure Data Access Workflow exists and grant pipeline has its workflowId (idempotent)
echo "Ensuring Data Access Workflow exists and pipeline YAML is set..."
if CREATE_OUTPUT=$(python scripts/data_access/create_data_access_workflow.py 2>&1); then
  if [[ "$CREATE_OUTPUT" =~ urn:li:actionWorkflow:([a-f0-9-]+) ]]; then
    WORKFLOW_UUID="${BASH_REMATCH[1]}"
    PIPELINE_YAML="src/grant-external-permissions-pipeline.yaml"
    if [ -f "$PIPELINE_YAML" ]; then
      sed "s/\(workflowId: \"\)[^\"]*/\1$WORKFLOW_UUID\"/" "$PIPELINE_YAML" > "$PIPELINE_YAML.tmp" && mv "$PIPELINE_YAML.tmp" "$PIPELINE_YAML"
      echo "Updated $PIPELINE_YAML with workflowId: $WORKFLOW_UUID"
    fi
  fi
else
  echo "Note: Could not create/update Data Access Workflow (run scripts/data_access/create_data_access_workflow.py and set workflowId in src/grant-external-permissions-pipeline.yaml if needed)."
fi

MOCK_CONTAINER=""
PIDS=()

cleanup() {
  echo ""
  echo "Stopping pipelines..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  if [ -n "$MOCK_CONTAINER" ]; then
    echo "Stopping mock server container..."
    docker stop $MOCK_CONTAINER 2>/dev/null || true
  fi
  exit 0
}
trap cleanup SIGINT SIGTERM

# Start mock server (Docker) if available
if command -v docker &>/dev/null; then
  echo "Building and starting mock server..."
  (cd mock-server && docker build -t grant-permissions-mock . -q)
  docker stop grant-permissions-mock 2>/dev/null || true
  docker run --rm -d -p 8000:8000 --name grant-permissions-mock --env-file .env grant-permissions-mock
  MOCK_CONTAINER="grant-permissions-mock"
  echo "Mock server: http://localhost:8000"
else
  echo "Docker not found; skipping mock server. Start it manually from mock-server/ if needed."
fi

# Start all four pipelines in background
PIPELINES=(
  src/grant-external-permissions-pipeline.yaml
  src/certification-event-pipeline.yaml
  src/metadata-proposal-pipeline.yaml
  src/glossary-proposal-pipeline.yaml
)
for config in "${PIPELINES[@]}"; do
  echo "Starting: $config"
  datahub actions -c "$config" &
  PIDS+=($!)
done

echo ""
echo "All four pipelines are running (PIDs: ${PIDS[*]})."
echo "Mock server: http://localhost:8000"
echo "Press Ctrl+C to stop pipelines and mock server."
echo ""

wait
