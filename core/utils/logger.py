from datetime import datetime


def log(text):

    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")