# Selective Image Encryption — PoC Skeleton

This is a minimal, **runnable** proof-of-concept skeleton for detecting PII regions and encrypting/redacting them per-region.

## What’s included
- **FastAPI** backend (Python) with endpoints:
  - `POST /ingest` — upload an image, returns detected regions (stubbed), redacts, and stores encrypted patches
  - `GET /images/{image_id}/manifest` — returns the manifest JSON for the image
  - `GET /images/{image_id}/redacted` — streams the redacted image
  - `POST /images/{image_id}/decrypt` — decrypts specific region(s) (requires `X-Role: Reviewer` header)
- **Postgres** database (via SQLAlchemy) for images, regions, and basic audit logs
- **Next.js** UI (minimal) to upload, preview overlays, and (optionally) decrypt regions when in Reviewer mode
- **Docker Compose** to run everything locally

> Note: Detection is intentionally **stubbed** in this skeleton to keep it small. It produces a couple of demo boxes per image. Replace `detect_regions_stub` with real pipeline calls (OCR/NER/layout/etc.) during the PoC.

## Quick start
```bash
# 1) From the project root:
docker compose build

# 2) Run the stack
docker compose up

# API: http://localhost:8000/docs
# UI:  http://localhost:3000
```

## Environment
- The API uses a fixed `APP_MASTER_KEY_HEX` in docker-compose for **PoC only**.
- Redacted images and encrypted region blobs are written to a data volume mounted at `/data`.

## Next steps
- Wire `detect_regions_stub` to your OCR/NER/layout fusion service.
- Swap local storage for MinIO/S3 and add presigned URLs for artifacts.
- Add JWT/OIDC and granular RBAC in place of the simple `X-Role` header.
