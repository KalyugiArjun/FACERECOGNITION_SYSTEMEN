# FaceAttend v2.0 — Improved Face Recognition System

## 🔧 Bugs Fixed (Kya Theek Kiya)

### 1. Label Map Bug (MAIN ACCURACY BUG)
**Problem:** Original `recognize.py` mein `imagePaths = os.listdir('dataset')` se naam liya jaata tha.
`os.listdir()` ka order guaranteed nahi hota — isliye galat student ka naam aata tha!

**Fix:** Ab `train.py` ek `labels.json` file save karta hai jisme ID→Name mapping properly stored hai.
`recognize.py` usi JSON se padhta hai. **Yahi sabse bada accuracy bug tha.**

### 2. Image Size Mismatch
**Problem:** `capture.py` 100×100 save karta tha, `recognize.py` 150×150 resize karta tha — mismatch!

**Fix:** Sab jagah **150×150** standardize kiya gaya hai.

### 3. Preprocessing Missing
**Problem:** Lighting conditions mein recognition fail hota tha.

**Fix:** Ab `cv2.equalizeHist()` (lighting normalize) + `cv2.GaussianBlur()` (noise reduce) dono use hote hain — 
**train aur recognize dono mein same preprocessing** taaki features match hon.

### 4. LBPH Parameters Improved
- `radius=2` (was 1) — zyada texture capture
- `grid_x=8, grid_y=8` (was 6×6) — finer pattern analysis

### 5. Confidence Threshold Fixed
**Problem:** Original mein threshold 70 tha — bahut lenient.

**Fix:** `55` — strict enough to avoid false positives, yet catches real faces.

### 6. More Training Images
**Problem:** Sirf 30 images train hoti thin.

**Fix:** Ab **60 images** capture hoti hain with instruction to move head slightly — varied angles = better model.

### 7. Login Error Handling
**Problem:** Login fail hone par blank/crash page aata tha.

**Fix:** Proper error message show hota hai.

### 8. Database Auto-Init
**Problem:** `database.db` missing hone par crash.

**Fix:** `init_db()` function tables auto-create karta hai.

---

## 📁 File Structure

```
FaceAttendance/
├── app.py              ← Flask backend (improved)
├── capture.py          ← Face capture (60 images, 150×150)
├── train.py            ← Training (saves labels.json)
├── recognize.py        ← Recognition (uses labels.json, preprocessing)
├── database.db         ← SQLite database
├── dataset/            ← Student face images
│   └── studentname/
│       └── 1.jpg, 2.jpg ...
├── trainer/
│   ├── trainer.yml     ← Trained LBPH model
│   └── labels.json     ← ID→Name mapping (NEW - fixes main bug)
└── templates/
    ├── login.html
    ├── register.html
    ├── student_dashboard.html
    ├── teacher_dashboard.html
    ├── principal_dashboard.html
    └── ...
```

## 🚀 Run Karne Ka Tarika

```bash
pip install flask opencv-contrib-python numpy
python app.py
```
Browser mein jaao: `http://127.0.0.1:5000`

## 👤 Default Accounts (add manually in DB)
- Teacher/Principal accounts `database.py` se add karo ya directly SQLite mein insert karo.

## 📸 Attendance Kaise Kaam Karta Hai
1. Student register karta hai → camera khulta hai → 60 photos capture hoti hain
2. Model automatically train hota hai
3. Teacher dashboard mein "Start Face Recognition" click karo
4. Camera khulega — students saamne aayein — attendance automatically mark ho jaayegi

## 💡 Tips for Better Accuracy
- Register karte waqt **achhi roshni** mein photo do
- Camera ke **seedha saamne** dekho
- Thoda **left-right, upar-niche** head move karo capture ke dauraan (varied angles)
- **Chaashma utaar ke** ek baar photos do (optional but helps)
