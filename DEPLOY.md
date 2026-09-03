# 🚀 ASU HostelCare — Live Server Deployment Guide (Aasan Tareeqa)

Yeh project **100% self-contained aur deployment-ready** hai! Backend aur Frontend ek hi server se chalte hain.

---

## ⚡ 1. Local Me Chalana (Super Easy)

### Windows Pe (Sirf 1-Click):
1. Folder me jaao aur `start.bat` par **double-click** karo!
2. Sab packages install honge aur server live ho jaayega.
3. Browser me kholo: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Terminal / Command Line Se:
```bash
# Dependencies install karo
pip install -r requirements.txt

# Server start karo (root main.py se)
python main.py
```

---

## 🌐 2. Render.com Pe Free Me Live Kaise Karein (Recommended)

Render.com par Python web services bilkul free me host hoti hain:

1. **GitHub pe push karo**:
   - Apne GitHub account me ek naya repository banao aur is code ko push kar do.
2. **Render.com par jao**:
   - [https://render.com](https://render.com) pe jaakar GitHub se Login karo.
   - **New +** button pe click karke **Web Service** choose karo.
   - Apna GitHub repository select karo.
3. **Settings fill karo**:
   - **Name**: `asu-hostelcare`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
4. **Deploy Web Service** par click karo!
   - 2 minute ke andar aapki website live ho jaayegi ek free domain ke saath (jaise `https://asu-hostelcare.onrender.com`).

*(Note: Is project me already `render.yaml` aur `Procfile` included hai, isliye Render isko automatically detect kar leta hai!)*

---

## 🚂 3. Railway.app Pe Live Kaise Karein

1. [https://railway.app](https://railway.app) pe jao aur GitHub se Login karo.
2. **New Project** -> **Deploy from GitHub repo** select karo.
3. Railway automatically `Dockerfile` ya `Procfile` detect karke live kar dega.
4. **Settings** -> **Generate Domain** pe click karo aur aapki website live!

---

## 🐳 4. Docker Se Chalana (Kisi bhi Cloud VPS pe)

Agar aapke paas DigitalOcean, AWS, GCP, ya koi bhi Linux VPS hai:

```bash
# 1-command me build aur run karo:
docker compose up -d --build
```
Aapka server background me port 8000 par live chalne lagega!

---

## 📄 5. Root `index.html` Ka Use

Project ke root folder me `index.html` file banayi gayi hai:
- Agar aap bina Python ke direct files dekhna chahte ho, to seedha `index.html` par double click karke browser me khol sakte ho.
- Agar aap kisi static host (GitHub Pages, Netlify, Vercel Static, cPanel public_html) par sirf frontend daalna chahte ho, to root `index.html` automatically landing page load kar deta hai.
