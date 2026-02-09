# File Vault

> **Secure document management system with intelligent PII redaction and AI-powered tax field extraction**

A full-stack cloud-native application built with Next.js and FastAPI, deployed on Google Cloud Platform. Features automated sensitive data protection, document approval workflows, and machine learning-based data extraction.

## Demo

https://github.com/user-attachments/assets/e6c2432e-23b6-47e8-b422-74e3d6afaf6e

**

> See the complete workflow in action: document upload, automatic PII redaction, AI-powered field extraction, and secure approval process.

---

## Features

### Core Functionality
- **🔐 Secure Authentication** - Google OAuth integration with NextAuth.js
- **📄 Document Upload** - Support for PDF tax documents with instant processing
- **🛡️ Automatic PII Redaction** - AI-powered detection and removal of sensitive information
  - Social Security Numbers (SSN)
  - Names and addresses
  - Phone numbers and email addresses
  - Dates of birth
- **✅ Approval Workflow** - Review redacted documents before vault storage
- **🤖 AI Field Extraction** - Vertex AI Gemini extracts structured tax data
  - Filing status
  - W-2 wages
  - Total deductions
  - IRA distributions
  - Capital gains/losses
- **📊 Structured Storage** - PostgreSQL database with audit trails
- **⚡ Rate Limiting** - Redis-based protection against abuse
- **📝 Comprehensive Audit Logging** - Cloud Logging integration

### Security
- Multi-layer PII protection with Google Cloud DLP API
- Document AI OCR with coordinate-based redaction
- Secure validation after redaction (ensures no PII leakage)
- JWT-based API authentication
- Automatic file cleanup on rejection
- Encrypted environment variables

---

## Tech Stack

### Frontend
- **Framework:** Next.js 16.1.3 (App Router, React Server Components)
- **Runtime:** Node.js 22+ / React 19
- **Language:** TypeScript 5
- **Styling:** Tailwind CSS 4
- **Authentication:** NextAuth.js 5.0 (Google OAuth)
- **UI Components:** Custom components with Radix UI primitives
- **PDF Rendering:** react-pdf 10.3
- **Deployment:** Vercel

### Backend
- **Framework:** FastAPI 0.115+ (Python 3.11)
- **Validation:** Pydantic 2.10+
- **Authentication:** JWT tokens (RS256, python-jose)
- **Database ORM:** SQLAlchemy 2.0+
- **PDF Processing:** PyMuPDF 1.23+, pikepdf 8.11+
- **Deployment:** Google Cloud Run

### Cloud Services (GCP)
- **Cloud Storage** (google-cloud-storage 2.14+) - Document staging and vault buckets
- **Document AI** (google-cloud-documentai 2.24+) - OCR text extraction with coordinates
- **Cloud DLP API** (google-cloud-dlp 3.15+) - PII detection and classification
- **Vertex AI** (google-cloud-aiplatform 1.68) - Gemini 2.5 Pro for tax field extraction
- **Cloud SQL (PostgreSQL)** (cloud-sql-python-connector 1.7+) - Structured data storage
- **Secret Manager** (google-cloud-secret-manager 2.18+) - Secure credential management
- **Cloud Logging** (google-cloud-logging 3.10) - Centralized audit logging
- **Cloud Run** - Serverless backend deployment

### Infrastructure
- **Rate Limiting:** Upstash Redis (@upstash/ratelimit 2.0+)
- **Monitoring:** Cloud Logging
- **IAM:** Service accounts with least-privilege access

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Vercel)                    │
│  Next.js 16 + TypeScript + NextAuth.js + Tailwind CSS       │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS/JWT
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend API (Cloud Run)                    │
│              FastAPI + Pydantic + SQLAlchemy                 │
└─────┬──────────┬──────────┬──────────┬──────────┬───────────┘
      │          │          │          │          │
      ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
│  Cloud   │ │Document │ │  DLP   │ │ Vertex  │ │  Cloud   │
│ Storage  │ │   AI    │ │  API   │ │   AI    │ │   SQL    │
│(Staging/ │ │  (OCR)  │ │  (PII) │ │(Gemini) │ │(Postgres)│
│ Vault)   │ │         │ │        │ │         │ │          │
└──────────┘ └─────────┘ └────────┘ └─────────┘ └──────────┘
```

### Document Processing Flow

1. **Upload** → User uploads PDF to staging bucket
2. **OCR** → Document AI extracts text with bounding boxes
3. **PII Detection** → Cloud DLP identifies sensitive information
4. **Redaction** → Creates new PDF with PII removed (rasterized pages)
5. **Validation** → Re-scans redacted PDF to ensure no PII remains
6. **Approval** → User reviews redacted document
7. **Vault Storage** → Approved documents moved to secure vault
8. **AI Extraction** → Vertex AI Gemini extracts structured tax fields
9. **Database Storage** → Structured data saved to PostgreSQL

---

## Project Structure

```
file-vault-gcp/
├── frontend/                 # Next.js frontend application
│   ├── app/                 # Next.js app router
│   │   ├── api/            # API routes (proxy to backend)
│   │   ├── dashboard/      # Dashboard page
│   │   ├── approval/       # Document approval flow
│   │   └── view/           # Document viewer
│   ├── components/         # React components
│   ├── lib/                # Utilities (API client, auth, JWT)
│   └── middleware.ts       # NextAuth middleware
│
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   │   ├── upload.py   # Document upload & redaction
│   │   │   ├── approval.py # Approval workflow & extraction
│   │   │   └── documents.py # Document management
│   │   ├── services/       # Business logic
│   │   │   ├── redaction_service.py    # PII redaction
│   │   │   ├── extraction_service.py   # AI field extraction
│   │   │   ├── storage_service.py      # GCS operations
│   │   │   ├── database_service.py     # PostgreSQL
│   │   │   └── logging_service.py      # Audit logging
│   │   ├── models/         # Pydantic models
│   │   ├── auth.py         # JWT authentication
│   │   └── config.py       # Configuration
│   └── setup/              # Infrastructure scripts
│
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

---

## Getting Started

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **Google Cloud Platform** account with billing enabled
- **Upstash Redis** account (free tier)
- **Google OAuth** credentials

### Local Development Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/file-vault-gcp.git
cd file-vault-gcp
```

#### 2. Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
NEXTAUTH_SECRET=your_nextauth_secret_key
NEXTAUTH_URL=http://localhost:3000
BACKEND_API_URL=http://localhost:8000

# Upstash Redis
UPSTASH_REDIS_REST_URL=https://your-redis-url.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_redis_token
```

Start frontend:

```bash
npm run dev
```

Frontend runs on `http://localhost:3000`

#### 3. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
PROJECT_ID=your-gcp-project-id
STAGING_BUCKET=your-staging-bucket
VAULT_BUCKET=your-vault-bucket
DOCUMENT_AI_PROCESSOR_ID=your-processor-id
DOCUMENT_AI_LOCATION=us
VERTEX_AI_LOCATION=us-central1
DB_INSTANCE_NAME=your-db-instance
DB_NAME=your-database-name
DB_USER=your-db-user
DB_SECRET_NAME=your-secret-name
REGION=us-central1
NEXTAUTH_SECRET=same_as_frontend_secret
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

Configure GCP IAM permissions:

```bash
chmod +x backend/setup/configure_iam.sh
./backend/setup/configure_iam.sh
```

Start backend:

```bash
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

---

## Deployment

### Frontend (Vercel)

1. Push code to GitHub
2. Import project in Vercel dashboard
3. Add environment variables in Vercel settings
4. Deploy

### Backend (Cloud Run)

```bash
cd backend

gcloud run deploy file-vault-backend \
  --source . \
  --region us-central1 \
  --service-account file-vault-backend@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars PROJECT_ID=your-project-id \
  --set-env-vars STAGING_BUCKET=your-staging-bucket \
  --set-env-vars VAULT_BUCKET=your-vault-bucket \
  # ... add all other environment variables
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT_ID:REGION:INSTANCE_NAME
```

---

## Security Considerations

### PII Redaction Process
- **Secure by Default:** Rasterizes PDF pages (irreversible redaction)
- **Double Validation:** Re-scans redacted documents with DLP
- **Automatic Cleanup:** Deletes original files after redaction failure
- **No Data Leakage:** Redacted PDFs cannot reveal original text

### Authentication & Authorization
- Google OAuth for user authentication
- JWT tokens for API authentication
- Email-based user isolation (users only see their own documents)
- Rate limiting on all endpoints

### Audit Logging
- All operations logged to Cloud Logging
- User actions tracked (upload, approve, reject, download)
- Failed operations logged with error details
- IP addresses recorded for security analysis

---

## Environment Variables

<details>
<summary>Complete list of required environment variables</summary>

### Frontend
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `NEXTAUTH_SECRET` - NextAuth.js encryption key
- `NEXTAUTH_URL` - Frontend URL
- `BACKEND_API_URL` - Backend API URL
- `UPSTASH_REDIS_REST_URL` - Redis URL for rate limiting
- `UPSTASH_REDIS_REST_TOKEN` - Redis authentication token

### Backend
- `PROJECT_ID` - GCP project ID
- `STAGING_BUCKET` - GCS bucket for uploaded documents
- `VAULT_BUCKET` - GCS bucket for approved documents
- `DOCUMENT_AI_PROCESSOR_ID` - Document AI processor ID
- `DOCUMENT_AI_LOCATION` - Document AI location (us, eu, asia)
- `VERTEX_AI_LOCATION` - Vertex AI region
- `DB_INSTANCE_NAME` - Cloud SQL instance name
- `DB_NAME` - PostgreSQL database name
- `DB_USER` - Database user
- `DB_SECRET_NAME` - Secret Manager secret name for DB password
- `REGION` - GCP region
- `NEXTAUTH_SECRET` - Same as frontend (for JWT verification)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account key (local only)

</details>

---

## API Documentation

Once the backend is running, visit:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Key Endpoints

- `POST /upload` - Upload document
- `GET /approval` - List documents awaiting approval
- `POST /approval/{id}/approve` - Approve document
- `POST /approval/{id}/reject` - Reject document
- `GET /approval/extractions/{id}` - Get extracted tax fields
- `GET /documents` - List all documents
- `GET /approval/preview/{id}` - Get redacted PDF preview
- `GET /approval/download/{id}` - Download approved document

---

## Acknowledgments

- Google Cloud Platform for cloud infrastructure
- Vercel for frontend hosting
- Upstash for Redis infrastructure
- Next.js and FastAPI communities

---
