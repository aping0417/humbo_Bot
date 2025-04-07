import yt_dlp as youtube_dl

print("aquq")
ydl_opts = {
    "quiet": True,
    "extractaudio": True,
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "noplaylist": True,
}

url = "https://www.youtube.com/watch?v=HIb3xizoyP0&ab_channel=%E6%B2%92%E6%9C%89%E8%80%B3%E8%86%9C%E7%9A%84%E7%83%A4%E8%82%89men"


with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)

    # 打印出所有可用格式的信息
    for i, fmt in enumerate(info.get('formats', [])):
        print(f"Format {i}: {fmt['format_id']} - {fmt['ext']} - {fmt['url']}")

        print("sjiajsi")
