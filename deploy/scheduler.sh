#!/usr/bin/env bash
# ==============================================================================
# deploy/scheduler.sh - Create / Update Cloud Scheduler Job for Scan Endpoint
# ==============================================================================
# Sets up a Cloud Scheduler job triggering the Understudy Agent /scan endpoint
# every 30 minutes (cron: */30 * * * *) to detect overdue commitments and nudge.
#
# Usage:
#   ./deploy/scheduler.sh [PROJECT_ID] [REGION] [SERVICE_URL]
#
# Environment Variable Overrides:
#   PROJECT_ID       GCP Project ID (default: current gcloud project config)
#   REGION           GCP Region (default: asia-south1)
#   JOB_NAME         Cloud Scheduler job name (default: understudy-scan-job)
#   SERVICE_NAME     Cloud Run service name (default: understudy-agent)
#   SERVICE_URL      Cloud Run base URL (auto-detected if omitted)
#   SCHEDULE         Cron expression (default: "*/30 * * * *")
#   TIME_ZONE        Time zone for schedule (default: "UTC")
# ==============================================================================

set -euo pipefail

# Display help message
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat << 'EOF'
Usage: ./deploy/scheduler.sh [PROJECT_ID] [REGION] [SERVICE_URL]

Create or update a Google Cloud Scheduler job that triggers the /scan endpoint.

Arguments:
  PROJECT_ID    Google Cloud Project ID (optional if set in gcloud config)
  REGION        Google Cloud Region (default: asia-south1)
  SERVICE_URL   Cloud Run Service URL (e.g. https://understudy-agent-xyz.run.app)
                If omitted, automatically queried from Cloud Run.

Environment Variables:
  PROJECT_ID    Target GCP Project ID
  REGION        Target GCP Region (default: asia-south1)
  JOB_NAME      Scheduler job name (default: understudy-scan-job)
  SCHEDULE      Cron schedule (default: "*/30 * * * *")
  TIME_ZONE     Cron time zone (default: "UTC")

Example:
  ./deploy/scheduler.sh my-gcp-project asia-south1
EOF
  exit 0
fi

# Resolve parameters
PROJECT_ID="${1:-${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}}"
REGION="${2:-${REGION:-asia-south1}}"
JOB_NAME="${JOB_NAME:-understudy-scan-job}"
SERVICE_NAME="${SERVICE_NAME:-understudy-agent}"
SCHEDULE="${SCHEDULE:-*/30 * * * *}"
TIME_ZONE="${TIME_ZONE:-UTC}"
SERVICE_URL="${3:-${SERVICE_URL:-}}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "❌ Error: GCP Project ID is required."
  echo "Provide it as an argument, set \$PROJECT_ID, or run 'gcloud config set project <PROJECT_ID>'."
  echo "Usage: ./deploy/scheduler.sh [PROJECT_ID] [REGION] [SERVICE_URL]"
  exit 1
fi

# Auto-detect service URL if not provided
if [[ -z "${SERVICE_URL}" ]]; then
  echo "🔍 Looking up Cloud Run service URL for '${SERVICE_NAME}' in region '${REGION}'..."
  SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format="value(status.url)" 2>/dev/null || true)
  
  if [[ -z "${SERVICE_URL}" ]]; then
    echo "❌ Error: Could not determine Cloud Run service URL for '${SERVICE_NAME}'."
    echo "Make sure the service is deployed or provide the URL as the 3rd argument."
    echo "Usage: ./deploy/scheduler.sh ${PROJECT_ID} ${REGION} https://<service-url>"
    exit 1
  fi
fi

TARGET_URI="${SERVICE_URL%/}/scan"

echo "======================================================================"
echo "⏰ Configuring Cloud Scheduler Cron Job"
echo "======================================================================"
echo "  Project ID:      ${PROJECT_ID}"
echo "  Location/Region: ${REGION}"
echo "  Job Name:        ${JOB_NAME}"
echo "  Schedule:        ${SCHEDULE} (every 30 minutes)"
echo "  Timezone:        ${TIME_ZONE}"
echo "  Target URI:      ${TARGET_URI}"
echo "  HTTP Method:     POST"
echo "======================================================================"

# Check if the scheduler job already exists
if gcloud scheduler jobs describe "${JOB_NAME}" --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  echo "🔄 Job '${JOB_NAME}' already exists. Updating configuration..."
  gcloud scheduler jobs update http "${JOB_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="${SCHEDULE}" \
    --time-zone="${TIME_ZONE}" \
    --uri="${TARGET_URI}" \
    --http-method="POST" \
    --headers="Content-Type=application/json" \
    --description="Triggers Understudy commitment follow-up scan every 30 minutes"
else
  echo "✨ Creating new Cloud Scheduler job '${JOB_NAME}'..."
  gcloud scheduler jobs create http "${JOB_NAME}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="${SCHEDULE}" \
    --time-zone="${TIME_ZONE}" \
    --uri="${TARGET_URI}" \
    --http-method="POST" \
    --headers="Content-Type=application/json" \
    --description="Triggers Understudy commitment follow-up scan every 30 minutes"
fi

echo "======================================================================"
echo "✅ Cloud Scheduler job configured successfully!"
echo "To test execution immediately:"
echo "  gcloud scheduler jobs run ${JOB_NAME} --project=${PROJECT_ID} --location=${REGION}"
echo "======================================================================"
