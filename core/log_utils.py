import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def append_log(file_name: str, lines):
    """
    file_name: 要寫入的檔名，例如 'anonymous_messages.log'
    lines: 可以是一個字串，或 list[字串]
    """
    if isinstance(lines, str):
        text = lines
    else:
        text = "\n".join(str(x) for x in lines)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = os.path.join(LOG_DIR, file_name)

    # 以「追加」模式寫入，檔案不存在會自動建立
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}]\n{text}\n\n")
