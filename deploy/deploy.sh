#!/usr/bin/env bash
# ==============================================================================
# deploy/deploy.sh - Deploy Understudy Agent to Google Cloud Run
# ==============================================================================
# Deploys the understudy-agent service to Cloud Run with Vertex AI GenAI and
# real Google Cloud Firestore connectivity.
#
# Usage:
#   ./deploy/deploy.sh [PROJECT_ID] [REGION]
#
# Environment Variable Overrides:
#   PROJECT_ID            GCP Project ID (default: current gcloud project config)
#   REGION                GCP Region (default: asia-south1)
#   SERVICE_NAME          Cloud Run service name (default: understudy-agent)
#   GOOGLE_CLOUD_LOCATION Vertex AI location (default: global)
#   SLACK_BOT_TOKEN       (Optional) Slack Bot User OAuth Token
#   SLACK_SIGNING_SECRET  (Optional) Slack Signing Secret
# ==============================================================================

set -euo pipefail

# Display help message
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat << 'EOF'
Usage: ./deploy/deploy.sh [PROJECT_ID] [REGION]

Deploy Understudy Agent to Google Cloud Run.

Arguments:
  PROJECT_ID   Google Cloud Project ID (optional if set in gcloud config or env)
  REGION       Google Cloud Region (default: asia-south1)

Environment Variables:
  PROJECT_ID            Target GCP Project ID
  REGION                Target GCP Region (default: asia-south1)
  SERVICE_NAME          Cloud Run service name (default: understudy-agent)
  GOOGLE_CLOUD_LOCATION Vertex AI location (default: global)
  SLACK_BOT_TOKEN       Slack Bot User OAuth Token (xoxb-...)
  SLACK_SIGNING_SECRET  Slack Request Signing Secret

Example:
  ./deploy/deploy.sh my-gcp-project asia-south1
EOF
  exit 0
fi

# Locate repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Resolve parameters
PROJECT_ID="${1:-${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}}"
REGION="${2:-${REGION:-asia-south1}}"
SERVICE_NAME="${SERVICE_NAME:-understudy-agent}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "❌ Error: GCP Project ID is required."
  echo "Provide it as an argument, set \$PROJECT_ID, or run 'gcloud config set project <PROJECT_ID>'."
  echo "Usage: ./deploy/deploy.sh [PROJECT_ID] [REGION]"
  exit 1
fi

echo "======================================================================"
echo "🚀 Deploying Understudy Agent to Google Cloud Run"
echo "======================================================================"
echo "  Project ID:           ${PROJECT_ID}"
echo "  Region:               ${REGION}"
echo "  Service Name:         ${SERVICE_NAME}"
echo "  Vertex AI Location:   ${GOOGLE_CLOUD_LOCATION}"
echo "  Firestore:            Real Google Cloud Firestore"
echo "  Source Directory:     ${REPO_ROOT}"
echo "======================================================================"

# Build environment variables list
ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=TRUE"
ENV_VARS="${ENV_VARS},GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
ENV_VARS="${ENV_VARS},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}"
ENV_VARS="${ENV_VARS},USE_REAL_FIRESTORE=true"

# Pass through Slack secrets if available
if [[ -n "${SLACK_BOT_TOKEN:-}" ]]; then
  ENV_VARS="${ENV_VARS},SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}"
  echo "  Slack Bot Token:      Configured"
fi
if [[ -n "${SLACK_SIGNING_SECRET:-}" ]]; then
  ENV_VARS="${ENV_VARS},SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET}"
  echo "  Slack Signing Secret: Configured"
fi
if [[ -n "${SLACK_APP_TOKEN:-}" ]]; then
  ENV_VARS="${ENV_VARS},SLACK_APP_TOKEN=${SLACK_APP_TOKEN}"
  echo "  Slack App Token:      Configured"
fi

cd "${REPO_ROOT}"

echo "📦 Submitting build and deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="." \
  --platform="managed" \
  --allow-unauthenticated \
  --port="8080" \
  --set-env-vars="${ENV_VARS}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo "======================================================================"
echo "✅ Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo "Health Check: curl ${SERVICE_URL}/health"
echo "Scan Trigger: curl -X POST ${SERVICE_URL}/scan"
echo "======================================================================"
