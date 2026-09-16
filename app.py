import hashlib
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DATA_FILE = Path(__file__).parent / "guestboard.json"
_lock = threading.Lock()


def load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_entries(entries: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/")
def index(request: Request, error: str | None = None):
    entries = load_entries()
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return templates.TemplateResponse(
        request,
        "guestboard.html",
        {"entries": entries, "error": error},
    )


@app.post("/add")
def add(
    request: Request,
    name: str = Form(...),
    message: str = Form(...),
    password: str = Form(...),
):
    name = name.strip()
    message = message.strip()

    if not name or not message or not password:
        return RedirectResponse("/?error=이름, 내용, 비밀번호를 모두 입력해주세요.", status_code=303)

    entries = load_entries()
    entries.append(
        {
            "id": uuid.uuid4().hex,
            "name": name[:20],
            "message": message[:500],
            "password_hash": hash_password(password),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ip": get_client_ip(request),
        }
    )

    with _lock:
        save_entries(entries)

    return RedirectResponse("/", status_code=303)


@app.post("/delete/{entry_id}")
def delete(entry_id: str, password: str = Form(...)):
    entries = load_entries()
    target = next((e for e in entries if e["id"] == entry_id), None)

    if target is None or target["password_hash"] != hash_password(password):
        return RedirectResponse("/?error=비밀번호가 일치하지 않습니다.", status_code=303)

    entries = [e for e in entries if e["id"] != entry_id]

    with _lock:
        save_entries(entries)

    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
