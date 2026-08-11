# Artist State

```bash

## ساختار پروژه
artist_site/
├── app.py              ← اپلیکیشن Flask + روت‌ها + زمان‌بند روزانه + منطق آپدیت آمار
├── models.py            ← مدل‌های دیتابیس (Artist, Album, Track, ViewStat)
├── seed_data.py         ← وارد کردن اطلاعات اولیه آرتیست/آلبوم/ترک
├── scraper/
│   ├── youtube_music_scraper.py
│   ├── soundcloud_scraper.py
│   └── spotify_scraper.py
├── templates/            ← قالب‌های HTML (راست‌به‌چپ، فارسی)
└── static/                ← CSS و JS



## نصب
cd "C:\Users\Hamed\Desktop\Artist State"
python -m venv venv
myenv\Scripts\activate
pip install -r requirements.txt
python app.py

### صفحه اصلی سایت
http://localhost:5000


### اجرای مهاجرت‌های دیتابیس
cd "C:\Users\Hamed\Desktop\Artist State"
myenv\Scripts\activate
set FLASK_APP=app:create_app
python -m flask db upgrade

### ذخیره در گیتهاب  
git add .
git commit -m "Final update for Railway"
git push origin main

