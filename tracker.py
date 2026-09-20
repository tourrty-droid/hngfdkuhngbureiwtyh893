import os
import json
import requests
from datetime import datetime, timezone

# ============ CONFIG / НАСТРОЙКИ ============
BOT_TOKEN = os.environ["BOT_TOKEN"]              # токен бота (секрет)
CHAT_ID   = os.environ["CHAT_ID"]                # id канала: -100xxxxxxxxxx

BADGE_ID  = 2701017739640148
BADGE_URL = f"https://www.roblox.com/badges/{BADGE_ID}/"
BADGE_RU  = "Secret Quest: The Signature Shedletsky Secret"
BADGE_EN  = "Secret Quest: The Signature Shedletsky Secret"

STATE_FILE = "state.json"
API        = f"https://badges.roblox.com/v1/badges/{BADGE_ID}/owners"
HEADERS    = {"User-Agent": "Mozilla/5.0 (badge-tracker)"}

MAX_USERS_PER_MESSAGE = 30   # сколько юзеров в одном сообщении
# ===========================================


def send(text: str) -> None:
    """Отправить сообщение в канал."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if not r.ok:
            print("telegram error:", r.status_code, r.text[:300])
    except Exception as e:
        print("telegram exception:", e)


def fetch_owners() -> list[dict]:
    """Все владельцы бейджа через пагинацию Roblox API."""
    owners, cursor = [], ""
    while True:
        params = {"limit": 100, "sortOrder": "Asc"}
        if cursor:
            params["cursor"] = cursor
        try:
            r = requests.get(API, headers=HEADERS, params=params, timeout=20)
        except Exception as e:
            print("roblox request exception:", e)
            break
        if r.status_code != 200:
            print("roblox error:", r.status_code, r.text[:200])
            break
        data = r.json()
        for u in data.get("data", []):
            owners.append({"id": u["id"], "name": u.get("name", "unknown")})
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
    return owners


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("state load error:", e)
    return {"seen": [], "initialized": False}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def format_new_users(users: list[dict]) -> str:
    """Двуязычное сообщение о новых владельцах бейджа."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(users)

    lines = []
    lines.append("🔔 <b>Новые владельцы бейджа</b> / <b>New badge owners</b>")
    lines.append(f"📊 {total}")
    lines.append("")

    lines.append("🏷 <b>Бейдж / Badge:</b>")
    lines.append(f"RU: {BADGE_RU}")
    lines.append(f"EN: {BADGE_EN}")
    lines.append(f'🔗 <a href="{BADGE_URL}">{BADGE_URL}</a>')
    lines.append("")

    lines.append("👤 <b>Пользователи / Users:</b>")
    for u in users:
        uid, name = u["id"], u["name"]
        lines.append(
            f'• <a href="https://www.roblox.com/users/{uid}/profile">{name}</a>'
            f' <code>({uid})</code>'
        )

    lines.append("")
    lines.append(f"🕒 {now}")
    return "\n".join(lines)


def main() -> None:
    state = load_state()
    seen = set(state.get("seen", []))
    owners = fetch_owners()
    print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}] owners fetched: {len(owners)}")

    # Первый запуск — просто запоминаем всех, никого не уведомляем
    if not state.get("initialized"):
        state["seen"] = [u["id"] for u in owners]
        state["initialized"] = True
        save_state(state)
        send(
            "✅ <b>Трекер запущен</b> / <b>Tracker started</b>\n"
            f"Взято на учёт / Tracking: <b>{len(owners)}</b> "
            "владельцев бейджа / badge owners.\n\n"
            f'🔗 <a href="{BADGE_URL}">{BADGE_URL}</a>'
        )
        return

    new_users = [u for u in owners if u["id"] not in seen]

    if new_users:
        # если новых много — бьём на пачки, чтобы не упереться в лимит Telegram
        for i in range(0, len(new_users), MAX_USERS_PER_MESSAGE):
            chunk = new_users[i:i + MAX_USERS_PER_MESSAGE]
            send(format_new_users(chunk))

        for u in new_users:
            seen.add(u["id"])

    state["seen"] = list(seen)
    save_state(state)
    print(f"new users: {len(new_users)}")


if __name__ == "__main__":
    main()
