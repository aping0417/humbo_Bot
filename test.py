import yt_dlp as youtube_dl

print("aquq")
ydl_opts = {
    "quiet": True,
    "extractaudio": True,
    "outtmpl": "downloads/%(title)s.%(ext)s",
    "noplaylist": True,
}

url = "https://www.youtube.com/watch?v=VhCkbbyrxoQ&ab_channel=%E9%9F%BFHibikiChannel"


with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)

    # 打印出所有可用格式的信息
    for i, fmt in enumerate(info.get('formats', [])):
        print(f"Format {i}: {fmt['format_id']} - {fmt['ext']} - {fmt['url']}")

        print("sjiajsi")
