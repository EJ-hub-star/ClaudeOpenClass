import random
import uuid

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

games: dict[str, dict] = {}


def new_game() -> dict:
    return {
        "answer": random.randint(1, 100),
        "attempts": 0,
        "history": [],
        "won": False,
    }


def get_game(request: Request) -> tuple[str, dict]:
    session_id = request.cookies.get("session_id")
    if session_id is None or session_id not in games:
        session_id = str(uuid.uuid4())
        games[session_id] = new_game()
    return session_id, games[session_id]


@app.get("/")
def index(request: Request):
    session_id, game = get_game(request)

    response = templates.TemplateResponse(
        request,
        "number_game.html",
        {
            "attempts": game["attempts"],
            "history": game["history"],
            "won": game["won"],
            "message": (
                f"축하합니다! {game['attempts']}번 만에 정답을 맞추셨습니다."
                if game["won"]
                else None
            ),
            "message_class": "win" if game["won"] else "",
        },
    )
    response.set_cookie("session_id", session_id)
    return response


@app.post("/guess")
def guess(request: Request, guess: int = Form(...)):
    session_id, game = get_game(request)

    if not game["won"]:
        game["attempts"] += 1
        answer = game["answer"]

        if guess < answer:
            game["history"].append(f"{guess} → 낮습니다")
        elif guess > answer:
            game["history"].append(f"{guess} → 높습니다")
        else:
            game["won"] = True
            game["history"].append(f"{guess} → 정답!")

    response = RedirectResponse("/", status_code=303)
    response.set_cookie("session_id", session_id)
    return response


@app.get("/new")
def new(request: Request):
    session_id, _ = get_game(request)
    games[session_id] = new_game()
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("session_id", session_id)
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
