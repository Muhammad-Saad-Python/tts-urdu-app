import os
import hashlib
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, session
from dotenv import load_dotenv
from openai import OpenAI

# load .env if present
load_dotenv()

# Base path (normal Flask)
base_path = Path(__file__).parent

# Flask app setup
app = Flask(__name__,
            static_folder=str(base_path / "static"),
            template_folder=str(base_path / "templates"))
app.secret_key = os.getenv("FLASK_SECRET", "change-this-secret")
APP_PASSWORD = os.getenv("APP_PASSWORD", "mypassword")

# cache folder (persistent inside deployment environment)
CACHE_DIR = base_path / "generated"
CACHE_DIR.mkdir(exist_ok=True)

# Voices List
VOICES = [
    {"id": "alloy", "gender": "Male"},
    {"id": "ash", "gender": "Male"},
    {"id": "ballad", "gender": "Female"},
    {"id": "coral", "gender": "Female"},
    {"id": "echo", "gender": "Male"},
    {"id": "fable", "gender": "Female"},
    {"id": "onyx", "gender": "Male"},
    {"id": "nova", "gender": "Female"},
    {"id": "sage", "gender": "Female"},
    {"id": "shimmer", "gender": "Female"},
    {"id": "verse", "gender": "Male"},
]

DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_FORMAT = "mp3"  # or "wav" / "opus"

# Middleware: protect all routes except /login and static
@app.before_request
def require_login():
    if request.endpoint not in ("login", "static") and "logged_in" not in session:
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Wrong password")
    return render_template("login.html")

# OpenAI client factory
def make_client_from_env():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    else:
        return OpenAI()

# initial client
client = make_client_from_env()

# ---------- Routes ----------
@app.get("/")
def index():
    return render_template("index.html", voices=VOICES, default_voice="alloy")

@app.post("/api/tts")
def tts():
    global client
    client = make_client_from_env()

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = (data.get("voice") or "alloy").strip()
    fmt = (data.get("format") or DEFAULT_FORMAT).strip()

    if not text:
        return jsonify({"ok": False, "error": "Text is required."}), 400

    # ✅ Step 1: Translate everything into Urdu
    try:
        translation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Translate everything into Urdu."},
                {"role": "user", "content": text}
            ]
        )
        urdu_text = translation.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({"ok": False, "error": f"Translation failed: {e}"}), 500

    # ✅ Step 2: TTS in Urdu
    cache_key = hashlib.sha256(f"{voice}|{fmt}|{urdu_text}".encode("utf-8")).hexdigest()[:24]
    outfile = CACHE_DIR / f"{cache_key}.{fmt}"

    if not outfile.exists():
        try:
            with client.audio.speech.with_streaming_response.create(
                model=DEFAULT_MODEL,
                voice=voice,
                input=urdu_text,
                response_format=fmt,
            ) as response:
                response.stream_to_file(str(outfile))
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "url": f"/audio/{outfile.name}", "urdu_text": urdu_text})


@app.get("/audio/<filename>")
def serve_audio(filename: str):
    path = CACHE_DIR / filename
    if not path.exists():
        return jsonify({"ok": False, "error": "File not found."}), 404

    if filename.endswith(".mp3"):
        mime = "audio/mpeg"
    elif filename.endswith(".wav"):
        mime = "audio/wav"
    elif filename.endswith(".opus"):
        mime = "audio/ogg"
    else:
        mime = "application/octet-stream"

    return send_file(path, mimetype=mime, as_attachment=False, conditional=True)



if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
