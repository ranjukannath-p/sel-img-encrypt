import easyocr
import mediapipe as mp
import cv2
import numpy as np

def detect_text_regions(image_path):
    """Detect text regions using EasyOCR."""
    reader = easyocr.Reader(['en'])
    results = reader.readtext(image_path)
    regions = []
    for (bbox, text, confidence) in results:
        regions.append({
            "type": "TEXT",
            "polygon": bbox,
            "confidence": confidence,
            "text": text
        })
    return regions

def detect_face_regions(image_path):
    """Detect face regions using Mediapipe."""
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils

    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    regions = []
    with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        results = face_detection.process(image_rgb)
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = image.shape
                x, y, w, h = int(bboxC.xmin * iw), int(bboxC.ymin * ih), int(bboxC.width * iw), int(bboxC.height * ih)
                regions.append({
                    "type": "FACE",
                    "polygon": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                    "confidence": detection.score[0]
                })
    return regions

def detect_pii(image_path):
    """Detect both text and face regions."""
    text_regions = detect_text_regions(image_path)
    face_regions = detect_face_regions(image_path)
    return text_regions + face_regions
