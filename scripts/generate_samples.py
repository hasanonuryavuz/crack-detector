"""Generate deterministic illustrative panels, NOT real industrial data."""
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def generate():
    target = ROOT / "samples"
    target.mkdir(exist_ok=True)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 1.4, (600, 900))
    gradient = np.linspace(174, 195, 900)[None, :]
    gray = np.clip(gradient + noise, 0, 255).astype(np.uint8)
    base = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    cv2.rectangle(base, (24, 24), (875, 575), (125, 125, 125), 3)
    images = {"clean": base, "crack": base.copy(), "scratch": base.copy()}
    points = np.array([[280,160],[325,195],[355,230],[400,260],[430,300],[470,320],[510,360],[535,395]], np.int32)
    cv2.polylines(images["crack"], [points], False, (30,30,30), 3, cv2.LINE_AA)
    cv2.line(images["crack"], (430,300), (435,260), (50,50,50), 2, cv2.LINE_AA)
    cv2.line(images["scratch"], (230,360), (650,300), (45,45,45), 2, cv2.LINE_AA)
    for name, image in images.items():
        cv2.imwrite(str(target / f"{name}.png"), image)


if __name__ == "__main__":
    generate()
