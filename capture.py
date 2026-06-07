import cv2
import os
import sys
import time

# ============================================================
# NAME
# ============================================================
if len(sys.argv) >= 2:
    name = sys.argv[1].strip().lower()
else:
    name = input("Enter Student Name: ").strip().lower()

if not name:
    print("❌ Invalid name")
    exit()

# ============================================================
# FOLDER
# ============================================================
path = os.path.join("dataset", name)
os.makedirs(path, exist_ok=True)
existing = len(os.listdir(path))

# ============================================================
# CAMERA
# ============================================================
cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("❌ Camera not detected")
    exit()

cam.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
time.sleep(1.5)

detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# ============================================================
# Capture more images (60) for better training variety
# ============================================================
MAX_IMAGES  = 60
count       = 0
SAVE_SIZE   = (150, 150)   # must match train.py + recognize.py

cv2.namedWindow("FaceAttend — Capture", cv2.WINDOW_NORMAL)
print(f"📷 Capturing for '{name}' — move head slightly for variety, ESC to stop")

while True:
    ret, frame = cam.read()
    if not ret:
        break

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=6,
        minSize=(100, 100)
    )

    if len(faces) > 0:
        (x, y, w, h) = faces[0]
        face_crop = gray[y:y+h, x:x+w]
        face_crop = cv2.resize(face_crop, SAVE_SIZE)

        # Save raw crop — train.py will preprocess
        save_idx  = existing + count + 1
        cv2.imwrite(os.path.join(path, f"{save_idx}.jpg"), face_crop)
        count += 1

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 220, 80), 2)

    # HUD
    progress = int((count / MAX_IMAGES) * (frame.shape[1] - 40))
    cv2.rectangle(frame, (20, frame.shape[0]-30), (frame.shape[1]-20, frame.shape[0]-15), (60,60,60), -1)
    if progress > 0:
        cv2.rectangle(frame, (20, frame.shape[0]-30), (20+progress, frame.shape[0]-15), (0,220,80), -1)

    cv2.putText(frame, f"Capturing: {count}/{MAX_IMAGES}",
                (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,220,80), 2)
    cv2.putText(frame, f"Student: {name.title()}",
                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
    cv2.putText(frame, "Move head slightly for variety | ESC to stop",
                (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,180,180), 1)

    cv2.imshow("FaceAttend — Capture", frame)

    if cv2.waitKey(1) == 27 or count >= MAX_IMAGES:
        break

cam.release()
cv2.destroyAllWindows()

print(f"✅ Captured {count} images for '{name}'")
print("⚡ Starting training...")
os.system("python train.py")
print("🎯 Done!")
