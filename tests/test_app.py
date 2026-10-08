from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest

from app import create_app
from detector import Settings, analyze, decode_image

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_home_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json == {"status": "ok"}


@pytest.mark.parametrize("name,expected", [("clean",False),("crack",True),("scratch",True)])
def test_demo_behavior(client, name, expected):
    response = client.post(f"/api/demo/{name}")
    assert response.status_code == 200
    data = response.json
    assert bool(data["count"]) is expected
    assert data["status"] == ("review" if expected else "no_candidate")
    assert data["analysis_size"] == [900,600]
    assert data["images"]["overlay"]


def test_uploaded_png_matches_demo(client):
    data = (ROOT / "samples" / "crack.png").read_bytes()
    response = client.post("/api/analyze", data={"image": (BytesIO(data),"image.png")})
    assert response.status_code == 200
    assert response.json["count"] == client.post("/api/demo/crack").json["count"]


def test_missing_and_invalid_file(client):
    assert client.post("/api/analyze").status_code == 400
    response = client.post("/api/analyze", data={"image":(BytesIO(b"bad data"),"fake.png")})
    assert response.status_code == 400
    assert "error" in response.json


@pytest.mark.parametrize("settings", [{"low":"150","high":"50"},{"margin":"31"},
                                      {"min_length":"oops"},{"min_elongation":"nan"}])
def test_invalid_settings(client, settings):
    assert client.post("/api/demo/crack", data=settings).status_code == 400


def test_unknown_demo(client):
    assert client.post("/api/demo/../app.py").status_code == 404
    assert client.post("/api/demo/missing").status_code == 404


def test_size_limit(client):
    client.application.config["MAX_CONTENT_LENGTH"] = 1024
    response = client.post("/api/analyze",data={"image":(BytesIO(b"x"*2048),"large.png")})
    assert response.status_code == 413


def test_pixel_limit():
    from PIL import Image
    buffer = BytesIO()
    Image.new("L",(4000,3100)).save(buffer, format="PNG")
    with pytest.raises(ValueError, match="12 milyon"):
        decode_image(buffer.getvalue())


def test_long_image_resized():
    image = np.full((600,2000,3),180,np.uint8)
    result = analyze(image)
    assert result["input_size"] == [2000,600]
    assert result["analysis_size"] == [1400,420]
    assert result["count"] == 0


def test_short_mark_filtered():
    image = np.full((600,900,3),180,np.uint8)
    cv2.line(image,(300,300),(320,305),(20,20,20),2)
    assert analyze(image)["count"] == 0


def test_boundary_mark_excluded():
    image = np.full((600,900,3),180,np.uint8)
    cv2.line(image,(20,300),(300,300),(20,20,20),2)
    assert analyze(image,Settings(margin=8))["count"] == 0
