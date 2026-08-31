# Understudy Agent - Production Deployment Guide

This guide walks through deploying the Understudy Agent FastAPI server to **Google Cloud Run**, integrating with **Vertex AI** (Gemini) and **Google Cloud Firestore (Native Mode)**, and configuring **Google Cloud Scheduler** for autonomous 30-minute commitment scans and Slack nudges.

---

## Architecture Overview

```
                        +----------------------------------------+
                        |         Google Cloud Platform          |
                        |                                        |
  [Client / Webhook] ---> [ Cloud Run: understudy-agent (FastAPI)|
                        |   +-- Vertex AI (Gemini 2.5/3.5)       |
                        |   +-- Google Cloud Firestore (Native)  |
                        |   +-- Slack App / Webhooks             |
                        |                                        |
  [Cloud Scheduler]  ---> [ POST /scan (every 30 mins)           |
  (Cron: */30 * * * *)  +----------------------------------------+
```

---

## Prerequisites

1. **Google Cloud SDK (`gcloud`)** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
2. A **Google Cloud Project** with active billing.
3. Appropriate GCP IAM permissions (`roles/owner`, `roles/editor`, or administrative permissions for Cloud Run, Firestore, Vertex AI, and Cloud Scheduler).
4. (Optional) **Docker** installed if you wish to test container builds locally.

---

## Step 1: Set Your GCP Project and Region

Set your target GCP Project ID and preferred default region (default: `asia-south1`):

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="asia-south1"

gcloud config set project "${PROJECT_ID}"
gcloud config set run/region "${REGION}"
```

---

## Step 2: Enable Required GCP APIs

Enable Cloud Run, Cloud Build, Cloud Firestore, Vertex AI, Cloud Scheduler, and Artifact Registry:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  aiplatform.googleapis.com \
  cloudscheduler.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"
```

---

## Step 3: Provision Google Cloud Firestore

If Firestore is not yet initialized in your GCP project, provision a database in **Native Mode**:

```bash
gcloud firestore databases create \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --type=firestore-native
```

*(If you already have a Firestore database in your project, skip this step).*

To deploy Firestore security rules from the repository root:
```bash
firebase deploy --only firestore:rules --project="${PROJECT_ID}"
```

---

## Step 4: Configure IAM Roles & Service Account

Cloud Run services use the default Compute Engine service account (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`) or a dedicated service account.

Ensure the service account has access to Firestore and Vertex AI:

```bash
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Firestore User role
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"
```

---

## Step 5: Configure Production Environment Variables

Review the template at `deploy/.env.production.example`:

| Environment Variable | Recommended Value | Description |
| :--- | :--- | :--- |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | Routes Gemini model calls through Vertex AI |
| `GOOGLE_CLOUD_PROJECT` | `${PROJECT_ID}` | Target GCP Project ID |
| `GOOGLE_CLOUD_LOCATION` | `global` | Location for Vertex AI model endpoints |
| `USE_REAL_FIRESTORE` | `true` | Connects directly to Google Cloud Firestore (disables emulator) |
| `FIRESTORE_EMULATOR_HOST` | *(empty)* | Left unset/empty in production |
| `SLACK_BOT_TOKEN` | `xoxb-...` | (Optional) Slack Bot Token for nudges & notifications |
| `SLACK_SIGNING_SECRET` | `...` | (Optional) Slack Signing Secret for webhook verification |
| `PORT` | `8080` | Server listening port (Cloud Run sets this automatically) |

---

## Step 6: Build and Deploy to Cloud Run

Run the automated deployment script from the repository root:

```bash
chmod +x deploy/deploy.sh
./deploy/deploy.sh "${PROJECT_ID}" "${REGION}"
```

Or deploy manually via `gcloud`:

```bash
gcloud run deploy understudy-agent \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="." \
  --platform="managed" \
  --allow-unauthenticated \
  --port="8080" \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global,USE_REAL_FIRESTORE=true"
```

Upon completion, `gcloud` outputs your Service URL (e.g. `https://understudy-agent-abc123xyz-el.a.run.app`).

---

## Step 7: Create the Cloud Scheduler Cron Job

Set up the automated 30-minute cron job targeting `/scan`:

```bash
chmod +x deploy/scheduler.sh
./deploy/scheduler.sh "${PROJECT_ID}" "${REGION}"
```

The script automatically detects your deployed Cloud Run service URL and creates/updates a job named `understudy-scan-job` running on schedule `*/30 * * * *`.

To manually trigger and test the scheduler job:
```bash
gcloud scheduler jobs run understudy-scan-job \
  --project="${PROJECT_ID}" \
  --location="${REGION}"
```

---

## Step 8: Verification & Health Checks

1. **Verify Health Endpoint**:
   ```bash
   SERVICE_URL=$(gcloud run services describe understudy-agent --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)")
   curl "${SERVICE_URL}/health"
   ```
   **Expected Response:**
   ```json
   {"status":"healthy","service":"understudy-agent"}
   ```

2. **Verify Scan Endpoint**:
   ```bash
   curl -X POST "${SERVICE_URL}/scan"
   ```
   **Expected Response:**
   ```json
   {"status":"ok","nudged":[]}
   ```

3. **Verify Cloud Run Logs**:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=understudy-agent" --limit=25 --project="${PROJECT_ID}"
   ```

---

## Local Docker Container Testing (Optional)

To test the container build and execution locally before deploying to GCP:

1. **Build Container**:
   ```bash
   docker build -t understudy .
   ```

2. **Run Container Locally with Emulator or Credentials**:
   ```bash
   docker run -p 8080:8080 \
     -e PORT=8080 \
     -e GOOGLE_CLOUD_PROJECT=demo-understudy \
     -e FIRESTORE_EMULATOR_HOST=host.docker.internal:8080 \
     understudy
   ```
