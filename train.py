import cv2
import os
import numpy as np
import json

dataPath    = 'dataset'
trainerDir  = 'trainer'
trainerFile = os.path.join(trainerDir, 'trainer.yml')
labelFile   = os.path.join(trainerDir, 'labels.json')

os.makedirs(trainerDir, exist_ok=True)

# ============================================================
# LBPH PARAMS — tuned for better accuracy
# radius=2, neighbors=8, grid=8x8 captures more texture detail
# ============================================================
recognizer = cv2.face.LBPHFaceRecognizer_create(
    radius=2,
    neighbors=8,
    grid_x=8,
    grid_y=8
)

faces     = []
ids       = []
label_map = {}      # {id: name}   — saved to JSON so recognize.py is in sync
current_id = 0

print("⚡ Training started...")

for person_name in sorted(os.listdir(dataPath)):
    person_path = os.path.join(dataPath, person_name)
    if not os.path.isdir(person_path):
        continue

    label_map[current_id] = person_name
    count = 0

    for image_name in os.listdir(person_path):
        image_path = os.path.join(person_path, image_name)
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if img is None:
            continue

        # Preprocess identically to recognize.py
        img = cv2.resize(img, (150, 150), interpolation=cv2.INTER_CUBIC)
        img = cv2.equalizeHist(img)
        img = cv2.GaussianBlur(img, (3, 3), 0)

        faces.append(img)
        ids.append(current_id)
        count += 1

    print(f"  [{current_id}] {person_name}: {count} images")
    current_id += 1

if len(faces) == 0:
    print("❌ No training images found in dataset/")
    exit()

recognizer.train(faces, np.array(ids))
recognizer.save(trainerFile)

# Save label map as JSON (fix: recognize.py used imagePaths list order which is unreliable)
with open(labelFile, 'w') as f:
    json.dump({str(k): v for k, v in label_map.items()}, f, indent=2)

print(f"\n✅ Training complete!")
print(f"   Students trained : {current_id}")
print(f"   Total images     : {len(faces)}")
print(f"   Saved to         : {trainerFile}")
print(f"   Labels saved to  : {labelFile}")
