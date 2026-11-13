"""Кадры панели для презентации: табло кандидатов, лестница «хаб или прямые», полоса «Путь к №2», карта вылетов.

Снимает outputs/redwings_panel.html через Playwright и установленный Chrome, обрезает и скругляет углы.
Запуск: py -3.13 src/deck/panel_shots.py
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "archive" / "dashboards" / "redwings_panel_v2.html"
OUT = ROOT / "outputs" / "presentation" / "panel_shots"
CHROME = os.environ.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
SHOTS = {"board": ".board", "ladder": "#vs > div:not([class])", "runway": "#rwy", "reach": "#map"}


def rounded(path, radius, crop=None):
    im = Image.open(path).convert("RGBA")
    if crop:
        im = im.crop(crop(im))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), radius=radius, fill=255)
    im.putalpha(mask)
    im.save(path)
    return im.size


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, headless=True)
        pg = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        pg.goto(PANEL.as_uri(), wait_until="networkidle")
        pg.wait_for_timeout(2500)
        for name, sel in SHOTS.items():
            el = pg.locator(sel).first
            el.scroll_into_view_if_needed()
            pg.wait_for_timeout(2500 if name == "reach" else 400)
            el.screenshot(path=str(OUT / f"{name}.png"))
        b.close()
    # табло: строки 1–15 и вычеркнутые города, без пояснений к столбцам и без обрезанного справа столбца
    sizes = {
        "board": rounded(OUT / "board.png", 40, lambda im: (6, 6, int(im.size[0] * 0.87), int(im.size[1] * 0.725))),
        "ladder": rounded(OUT / "ladder.png", 24),
        "runway": rounded(OUT / "runway.png", 40),
        "reach": rounded(OUT / "reach.png", 40),
    }
    for k, v in sizes.items():
        print(k, v)


if __name__ == "__main__":
    main()
