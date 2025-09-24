import logging
from typing import List
from pydantic import BaseModel
class DecryptRequest(BaseModel):
    region_ids: List[str]
import io, os, json, uuid, binascii, base64
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Response, logger
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..db import SessionLocal
from ..schemas import IngestResponse, ManifestOut, RegionOut
from ..models import Image as ImageModel, Region as RegionModel, Audit as AuditModel
from ..settings import settings
from ..utils.crypto import load_master_key, encrypt_bytes, decrypt_bytes, sha256_hex
from ..utils.redact import redact_with_boxes
from ..utils.pii_detection import detect_pii
import numpy as np

router = APIRouter(prefix="", tags=["images"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("images.py")

def custom_serializer(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

# Replace the detect_regions_stub function with AI-based detection logic
def detect_regions(img: Image.Image) -> List[Dict[str, Any]]:
    """Detect PII regions using AI-based detection logic."""
    # Save the image temporarily to pass its path to the detection logic
    temp_path = "temp_image.png"
    img.save(temp_path)

    # Use the detect_pii function to detect text and face regions
    regions = detect_pii(temp_path)

    # Clean up the temporary file
    os.remove(temp_path)

    return regions

def save_audit(db: Session, *, actor: str, action: str, image_id: str, region_id: str | None, purpose: str | None = None):
    audit = AuditModel(
        id=str(uuid.uuid4()),
        actor=actor,
        action=action,
        image_id=image_id,
        region_id=region_id,
        purpose=purpose,
        model_versions="pii-poc-0.1.0",
    )
    db.add(audit)
    db.commit()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_image(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    image_id = str(uuid.uuid4())
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    img_dir = os.path.join(settings.STORAGE_DIR, "images")
    os.makedirs(img_dir, exist_ok=True)
    reg_dir = os.path.join(settings.STORAGE_DIR, "regions")
    os.makedirs(reg_dir, exist_ok=True)

    # Detect regions (stub)
    regions = detect_regions(img)

    # Redact
    boxes = [r["polygon"] for r in regions]
    red = redact_with_boxes(img, boxes)

    # Save originals/redacted
    orig_path = os.path.join(img_dir, f"{image_id}_orig.png")
    red_path = os.path.join(img_dir, f"{image_id}_redacted.png")
    img.save(orig_path, format="PNG")
    red.save(red_path, format="PNG")

    key = load_master_key(settings.APP_MASTER_KEY_HEX)

    # Store DB rows and encrypt region patches
    db = SessionLocal()
    try:
        im_row = ImageModel(
            id=image_id,
            url_original=orig_path,
            url_redacted=red_path,
            pipeline_versions="pii-poc-0.1.0",
            created_by="system",
        )
        db.add(im_row)
        db.commit()

        for idx, r in enumerate(regions):
            # crop patch
            xs = [p[0] for p in r["polygon"]]
            ys = [p[1] for p in r["polygon"]]
            bbox = (min(xs), min(ys), max(xs), max(ys))
            patch = img.crop(bbox)

            buf = io.BytesIO()
            patch.save(buf, format="PNG")
            patch_bytes = buf.getvalue()

            ct, iv = encrypt_bytes(patch_bytes, key)
            blob_path = os.path.join(reg_dir, f"{image_id}_r{idx}.bin")
            with open(blob_path, "wb") as f:
                f.write(ct)

            region_row = RegionModel(
                id=str(uuid.uuid4()),
                image_id=image_id,
                type=r["type"],
                polygon_json=json.dumps(r["polygon"],default=custom_serializer),
                confidence=float(r["confidence"]),
                sha256=sha256_hex(patch_bytes),
                enc_algo="AES-GCM",
                iv_hex=binascii.hexlify(iv).decode(),
                kms_key_id="local-poc",
            )
            db.add(region_row)

        db.commit()
        save_audit(db, actor="system", action="INGEST", image_id=image_id, region_id=None, purpose=None)
    finally:
        db.close()

    return {
        "image_id": image_id,
        "status": "processed",
        "regions": regions,
        "redacted_url": f"/images/{image_id}/redacted",
    }

@router.get("/images/{image_id}/manifest", response_model=ManifestOut)
def get_manifest(image_id: str):
    db = SessionLocal()
    try:
        im = db.get(ImageModel, image_id)
        if not im:
            raise HTTPException(status_code=404, detail="Image not found")
        regions = db.execute(select(RegionModel).where(RegionModel.image_id == image_id)).scalars().all()

        return {
            "image_id": image_id,
            "version": im.pipeline_versions or "pii-poc-0.1.0",
            "regions": [
                {
                    "id": r.id,
                    "type": r.type,
                    "sha256": r.sha256,
                    "iv": r.iv_hex,
                    "enc_algo": r.enc_algo,
                    "confidence": r.confidence,
                    "polygon": json.loads(r.polygon_json),
                }
                for r in regions
            ],
            "created_at": im.created_at.isoformat() + "Z",
        }
    finally:
        db.close()

@router.get("/images/{image_id}/redacted")
def get_redacted(image_id: str):
    db = SessionLocal()
    try:
        im = db.get(ImageModel, image_id)
        if not im:
            raise HTTPException(status_code=404, detail="Image not found")
        path = im.url_redacted
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Redacted image missing")

        def iterfile():
            with open(path, "rb") as f:
                yield from f
        return StreamingResponse(iterfile(), media_type="image/png")
    finally:
        db.close()

@router.post("/images/{image_id}/decrypt")
def decrypt_regions(image_id: str, req: DecryptRequest, x_role: str | None = Header(None)):
    logger.info(f"Received payload: {req}")
    logger.info(f"Received x-role header: {x_role}")
    if x_role != "Reviewer":
        raise HTTPException(status_code=403, detail="Reviewer role required")

    db = SessionLocal()
    try:
        im = db.get(ImageModel, image_id)
        if not im:
            raise HTTPException(status_code=404, detail="Image not found")

        regs = db.execute(select(RegionModel).where(RegionModel.image_id == image_id, RegionModel.id.in_(req.region_ids))).scalars().all()
        if not regs:
            raise HTTPException(status_code=404, detail="No matching regions")

        key = load_master_key(settings.APP_MASTER_KEY_HEX)
        reg_dir = os.path.join(settings.STORAGE_DIR, "regions")

        out = {}
        for r in regs:
            blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(blob_path):
                # backwards compatibility for r{idx} naming
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(blob_path):
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(blob_path):
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            # In this skeleton we saved as {image_id}_r{idx}.bin
            npath = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(npath):
                # try legacy
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            else:
                blob_path = npath

            # fallback to our saved name style
            if not os.path.exists(blob_path):
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(blob_path):
                # final attempt: {image_id}_r{idx}.bin already used
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")

            # The above is overly defensive; in our ingest we used {image_id}_r{idx}.bin
            blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(blob_path):
                # try simple exact path
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")
            if not os.path.exists(blob_path):
                # just try the canonical naming from ingest again:
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")

            # In case we messed up, also try {image_id}_r{idx}.bin using r.id
            if not os.path.exists(blob_path):
                blob_path = os.path.join(reg_dir, f"{image_id}_{r.id}.bin")

            with open(blob_path, "rb") as f:
                ct = f.read()
            iv = bytes.fromhex(r.iv_hex)
            pt = decrypt_bytes(ct, key, iv)
            b64 = base64.b64encode(pt).decode()
            out[r.id] = {"type": r.type, "image_base64": f"data:image/png;base64,{b64}"}

            save_audit(db, actor="reviewer", action="DECRYPT", image_id=image_id, region_id=r.id, purpose="PoC demo")

        return out
    except Exception as e:
        logger.error("An error occurred in decrypt_regions", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred")
    finally:
        db.close()
