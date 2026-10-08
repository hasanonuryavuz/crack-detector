"""Explainable Canny-based inspection of flat, low-texture surfaces."""
from dataclasses import dataclass
from io import BytesIO
import base64
import warnings

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

MAX_PIXELS = 12_000_000
MAX_SIDE = 1400


@dataclass(frozen=True)
class Settings:
    low: int = 50
    high: int = 130
    min_length: int = 60
    min_elongation: float = 3.0
    margin: int = 8

    def __post_init__(self):
        if not 0 <= self.low < self.high <= 255:
            raise ValueError("Canny eşikleri 0 ≤ alt < üst ≤ 255 olmalıdır.")
        if not 10 <= self.min_length <= 1000:
            raise ValueError("Minimum uzunluk 10–1000 piksel olmalıdır.")
        if not 1 <= self.min_elongation <= 20:
            raise ValueError("Uzunluk/en oranı 1–20 olmalıdır.")
        if not 0 <= self.margin <= 30:
            raise ValueError("Kenar payı %0–30 olmalıdır.")


def decode_image(data: bytes) -> np.ndarray:
    """Check dimensions before OpenCV allocates a decoded image."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise ValueError("Yalnızca JPEG ve PNG görselleri desteklenir.")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Görsel en fazla 12 milyon piksel olabilir.")
                if min(image.size) < 64:
                    raise ValueError("Görselin iki boyutu da en az 64 piksel olmalıdır.")
                image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning, SyntaxError) as exc:
        raise ValueError("Görsel okunamadı. Geçerli bir JPEG veya PNG yükleyin.") from exc
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Görsel çözümlenemedi.")
    return image


def png_base64(image: np.ndarray) -> str:
    ok, data = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("Sonuç görseli oluşturulamadı.")
    return base64.b64encode(data).decode("ascii")


def analyze(image: np.ndarray, settings: Settings = Settings()) -> dict:
    original_height, original_width = image.shape[:2]
    scale = min(1.0, MAX_SIDE / max(original_height, original_width))
    if scale < 1:
        image = cv2.resize(image, (max(1, round(original_width * scale)), max(1, round(original_height * scale))), interpolation=cv2.INTER_AREA)
    height, width = image.shape[:2]
    mx, my = int(width * settings.margin / 100), int(height * settings.margin / 100)
    roi = image[my:height-my, mx:width-mx]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, settings.low, settings.high, L2gradient=True)
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    overlay = image.copy()
    cv2.rectangle(overlay, (mx, my), (width-mx-1, height-my-1), (190, 160, 40), 1)
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # An object intersecting the ROI boundary is often the panel edge.
        if x <= 1 or y <= 1 or x+w >= roi.shape[1]-1 or y+h >= roi.shape[0]-1:
            continue
        (_, _), (a, b), _ = cv2.minAreaRect(contour)
        length, thickness = max(a, b), max(min(a, b), 1.0)
        elongation = length / thickness
        if length < settings.min_length or elongation < settings.min_elongation:
            continue
        moved = contour + np.array([[[mx, my]]], dtype=np.int32)
        cv2.drawContours(overlay, [moved], -1, (70, 70, 245), 2)
        cv2.rectangle(overlay, (x+mx-4, y+my-4), (x+mx+w+4, y+my+h+4), (70, 70, 245), 2)
        candidates.append({"box": {"x": x+mx, "y": y+my, "width": w, "height": h},
                           "length_px": round(length, 1), "elongation": round(elongation, 2)})
    candidates.sort(key=lambda c: c["length_px"], reverse=True)
    edge_full = np.zeros((height, width), np.uint8)
    edge_full[my:height-my, mx:width-mx] = edges
    return {"status": "review" if candidates else "no_candidate", "count": len(candidates),
            "candidates": candidates, "input_size": [original_width, original_height],
            "analysis_size": [width, height], "scale": round(scale, 5),
            "roi": {"x": mx, "y": my, "width": roi.shape[1], "height": roi.shape[0]},
            "edge_density_percent": round(100 * np.count_nonzero(edges) / edges.size, 2),
            "images": {"original": png_base64(image), "edges": png_base64(edge_full),
                       "overlay": png_base64(overlay)}}
