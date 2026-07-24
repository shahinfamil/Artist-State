from spotify_scraper import SpotifyClient

try:
    print("در حال اتصال به اسپاتیفای...")
    with SpotifyClient() as client:
        # تست با یک آهنگ نمونه
        track = client.get_track("https://open.spotify.com/track/3hqEJpp49MAylz2UyIkc3r")
        print("\nارتباط با موفقیت برقرار شد!")
        print("نام آهنگ:", track.name)
        print("اطلاعات خام آهنگ جهت بررسی فیلد بازدید:")
        print(track.to_dict())
except Exception as e:
    print("خطا در اجرا:", e)