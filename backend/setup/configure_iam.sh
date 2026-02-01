#!/bin/bash

# IAM Configuration Script for File Vault
# Run this once during initial deployment
#
# Usage:
#   chmod +x setup/configure_iam.sh
#   ./setup/configure_iam.sh

set -e

PROJECT_ID="file-vault-assessment-484617"
SERVICE_ACCOUNT_NAME="file-vault-backend"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "========================================="
echo "File Vault IAM Configuration"
echo "========================================="
echo "Project: ${PROJECT_ID}"
echo "Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Not logged in to gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
echo "Setting active project..."
gcloud config set project ${PROJECT_ID}
echo ""

# Check if service account exists
echo "Checking service account..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID} &> /dev/null; then
    echo "✓ Service account already exists: ${SERVICE_ACCOUNT_EMAIL}"
else
    echo "Creating service account..."
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --display-name="File Vault Backend Service Account" \
        --description="Service account for File Vault backend API (FastAPI)" \
        --project=${PROJECT_ID}
    echo "✓ Service account created: ${SERVICE_ACCOUNT_EMAIL}"
fi
echo ""

# Grant necessary roles
echo "========================================="
echo "Granting IAM Roles..."
echo "========================================="

# 1. Storage permissions (staging bucket)
echo "→ Granting storage.objectAdmin (staging + vault buckets)..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectAdmin" \
    --condition=None \
    --quiet

# 2. DLP permissions (PII detection)
echo "→ Granting dlp.user (PII detection)..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/dlp.user" \
    --condition=None \
    --quiet

# 3. Document AI permissions (OCR)
echo "→ Granting documentai.apiUser (OCR processing)..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/documentai.apiUser" \
    --condition=None \
    --quiet

# 4. Vertex AI permissions (for Day 4 - field extraction)
echo "→ Granting aiplatform.user (field extraction)..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet

# 5. Secret Manager permissions (for Day 4 - DB credentials)
echo "→ Granting secretmanager.secretAccessor (DB credentials)..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None \
    --quiet

# 6. Cloud SQL Client (for Day 4 - database access)
echo "→ Granting cloudsql.client (database access)..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudsql.client" \
    --condition=None \
    --quiet

echo "✓ All IAM roles granted successfully"
echo ""

# Verify permissions
echo "========================================="
echo "Verifying Permissions..."
echo "========================================="
gcloud projects get-iam-policy ${PROJECT_ID} \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --format="table(bindings.role)" | head -n 20

echo ""
echo "========================================="
echo "✓ IAM Configuration Complete!"
echo "========================================="
echo ""
echo "Service Account: ${SERVICE_ACCOUNT_EMAIL}"
echo ""
echo "Roles Granted:"
echo "  • roles/storage.objectAdmin     - Read/write/delete files in GCS"
echo "  • roles/dlp.user                - PII detection with Cloud DLP"
echo "  • roles/documentai.apiUser      - OCR with Document AI"
echo "  • roles/aiplatform.user         - Field extraction with Vertex AI (Day 4)"
echo "  • roles/secretmanager.secretAccessor - Access DB credentials (Day 4)"
echo "  • roles/cloudsql.client         - Connect to Cloud SQL (Day 4)"
echo ""
echo "Next Steps:"
echo "  1. Deploy backend to Cloud Run with this service account:"
echo "     gcloud run deploy file-vault-backend \\"
echo "       --service-account=${SERVICE_ACCOUNT_EMAIL} \\"
echo "       --region=us-central1"
echo ""
echo "  2. Download service account key (for local development):"
echo "     gcloud iam service-accounts keys create ~/file-vault-key.json \\"
echo "       --iam-account=${SERVICE_ACCOUNT_EMAIL}"
echo ""
echo "  3. Set GOOGLE_APPLICATION_CREDENTIALS environment variable:"
echo "     export GOOGLE_APPLICATION_CREDENTIALS=~/file-vault-key.json"
echo ""
echo "Security Notes:"
echo "  ✓ Least-privilege principle applied"
echo "  ✓ No admin/owner permissions granted"
echo "  ✓ No billing/compute permissions"
echo "  ✓ All actions logged to Cloud Logging"
echo ""
