import cv2
import os
import sqlite3
import numpy as np
import json
from datetime import datetime

# ============================================================
# PATHS
# ============================================================
dataPath    = 'dataset'
trainerFile = 'trainer/trainer.yml'
labelFile   = 'trainer/labels.json'

# ============================================================
# LOAD MODEL + LABEL MAP
# ============================================================
if not os.path.exists(trainerFile):
    print("❌ trainer.yml not found. Train first using train.py")
    exit()

if not os.path.exists(labelFile):
    print("❌ labels.json not found. Re-train using train.py")
    exit()

face_recognizer = cv2.face.LBPHFaceRecognizer_create()
face_recognizer.read(trainerFile)

with open(labelFile, 'r') as f:
    label_map = json.load(f)          # {str(id): name}

# ============================================================
# HAAR CASCADE (eye cascade added for better detection)
# ============================================================
faceCascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)
eyeCascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_eye.xml'
)

# ============================================================
# CONFIDENCE THRESHOLD
# LBPH: lower = better match. 0=perfect, 100=bad
# 55 is strict enough to avoid false positives
# ============================================================
CONFIDENCE_THRESHOLD = 55

# ============================================================
# ATTENDANCE HELPER
# ============================================================
marked = set()

def mark_attendance(name):
    if name in marked:
        return

    conn   = sqlite3.connect('database.db')
    cursor = conn.cursor()

    now  = datetime.now()
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    cursor.execute(
        "SELECT * FROM attendance WHERE name=? AND date=?", (name, date)
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO attendance(name,date,time) VALUES(?,?,?)",
            (name, date, time)
        )
        conn.commit()
        print(f"✅ Attendance marked: {name} at {time}")

    marked.add(name)
    conn.close()

# ============================================================
# PREPROCESSING — equalise + denoise for better recognition
# ============================================================
def preprocess(face_img):
    face_img = cv2.resize(face_img, (150, 150), interpolation=cv2.INTER_CUBIC)
    face_img = cv2.equalizeHist(face_img)                    # fix lighting
    face_img = cv2.GaussianBlur(face_img, (3, 3), 0)         # reduce noise
    return face_img

# ============================================================
# CAMERA
# ============================================================
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Camera not found!")
    exit()

# Boost resolution
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("📷 Recognition started — press ESC to quit")
cv2.namedWindow("FaceAttend — Recognition", cv2.WINDOW_NORMAL)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Detect faces — relaxed minNeighbors for detection, strict for recognition
    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80)
    )

    for (x, y, w, h) in faces:
        face_crop = gray[y:y+h, x:x+w]
        processed  = preprocess(face_crop)

        label_id, confidence = face_recognizer.predict(processed)

        # ---- GREEN = known, RED = unknown ----
        if confidence < CONFIDENCE_THRESHOLD:
            name   = label_map.get(str(label_id), "Unknown")
            pct    = max(0, int(100 - confidence))           # readability %
            color  = (0, 220, 80)
            text   = f"{name}  ({pct}%)"
            mark_attendance(name)
        else:
            color = (0, 0, 220)
            text  = f"Unknown  (conf:{int(confidence)})"

        # Draw box + label
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
        cv2.rectangle(frame, (x, y-30), (x+w, y), color, -1)
        cv2.putText(frame, text, (x+4, y-8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # HUD
    cv2.putText(frame, f"Marked: {len(marked)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 220, 80), 2)
    cv2.putText(frame, "ESC to exit", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    cv2.imshow("FaceAttend — Recognition", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
print(f"✅ Done. {len(marked)} student(s) marked.")
