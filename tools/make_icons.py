"""Genera los iconos PWA de RetailPOS Pro.

Fondo azul institucional y cinco barras blancas centradas, sin texto.
El contenido queda dentro del 80 % central para que sea apto como maskable.
"""
from pathlib import Path

from PIL import Image, ImageDraw

BLUE = (0, 102, 204)
WHITE = (255, 255, 255)
OUT = Path(__file__).resolve().parents[1] / "static" / "icons"
SIZES = (192, 512, 180)


def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), BLUE)
    draw = ImageDraw.Draw(image)

    bar_w = size * 0.052
    gap = size * 0.048
    heights = (0.34, 0.50, 0.28, 0.44, 0.36)
    total_w = len(heights) * bar_w + (len(heights) - 1) * gap
    x = (size - total_w) / 2
    center_y = size / 2

    for ratio in heights:
        height = size * ratio
        y0 = center_y - height / 2
        draw.rounded_rectangle(
            [x, y0, x + bar_w, y0 + height],
            radius=bar_w / 2,
            fill=WHITE,
        )
        x += bar_w + gap

    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        path = OUT / f"icon-{size}.png"
        draw_icon(size).save(path, "PNG", optimize=True)
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
