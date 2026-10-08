"""Flask routes; uploaded images are processed in memory, never saved."""
from pathlib import Path
from time import perf_counter

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from detector import Settings, analyze, decode_image

ROOT = Path(__file__).resolve().parent
DEMOS = {"clean": "clean.png", "crack": "crack.png", "scratch": "scratch.png"}


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    def settings_from_form():
        try:
            return Settings(low=int(request.form.get("low", 50)),
                            high=int(request.form.get("high", 130)),
                            min_length=int(request.form.get("min_length", 60)),
                            min_elongation=float(request.form.get("min_elongation", 3)),
                            margin=int(request.form.get("margin", 8)))
        except (ValueError, OverflowError) as exc:
            raise ValueError(str(exc) if "olmalıdır" in str(exc) else "Parametreler geçerli sayılar olmalıdır.") from exc

    def inspect_bytes(data):
        settings = settings_from_form()
        start = perf_counter()
        result = analyze(decode_image(data), settings)
        result["elapsed_ms"] = round((perf_counter() - start) * 1000, 1)
        return jsonify(result)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/analyze")
    def upload():
        file = request.files.get("image")
        if file is None or not file.filename:
            return jsonify(error="Bir görsel seçin."), 400
        return inspect_bytes(file.read())

    @app.post("/api/demo/<name>")
    def demo(name):
        if name not in DEMOS:
            return jsonify(error="Örnek bulunamadı."), 404
        return inspect_bytes((ROOT / "samples" / DEMOS[name]).read_bytes())

    @app.errorhandler(ValueError)
    def bad_input(exc):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(exc):
        return jsonify(error="İstek en fazla 8 MB olabilir."), 413

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
