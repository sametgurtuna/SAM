# SAM — Icon Generator (build-time tool)
# Renders assets/icon.ico from the same orb design the overlay uses, so the
# installer, the exe and the tray icon all look like the same product.
#
# Run once after changing the design:
#     python tools/make_icon.py
# The produced assets/icon.ico is committed (PyInstaller and Inno Setup both
# need a real file on disk — the tray icon is drawn at runtime, but an exe
# icon cannot be).

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import QApplication

ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]
RENDER_SIZE = 256

ACCENT = QColor("#00D4AA")
ACCENT_2 = QColor("#00BFFF")


def render_orb(size: int) -> QPixmap:
    """Draw the orb: glow, dark disc, teal ring, 'S'."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    cx = cy = size / 2.0
    disc_r = size * 0.38
    ring_r = size * 0.45

    # Outer glow
    glow = QRadialGradient(cx, cy, size / 2.0)
    inner = QColor(ACCENT)
    inner.setAlpha(110)
    mid = QColor(ACCENT)
    mid.setAlpha(40)
    outer = QColor(ACCENT)
    outer.setAlpha(0)
    glow.setColorAt(0.0, inner)
    glow.setColorAt(0.55, mid)
    glow.setColorAt(1.0, outer)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(glow)
    p.drawRect(QRectF(0, 0, size, size))

    # Core disc
    disc = QRadialGradient(cx, cy - disc_r * 0.25, disc_r * 1.4)
    disc.setColorAt(0.0, QColor(20, 24, 32))
    disc.setColorAt(0.7, QColor(10, 12, 18))
    disc.setColorAt(1.0, QColor(6, 8, 12))
    p.setBrush(disc)
    p.drawEllipse(QPointF(cx, cy), disc_r, disc_r)

    # Ring — blue-green gradient sweep, approximated by two arcs
    from PyQt6.QtGui import QPen
    pen_w = max(1.0, size * 0.035)
    ring_rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(ACCENT, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(ring_rect, 200 * 16, 200 * 16)
    p.setPen(QPen(ACCENT_2, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawArc(ring_rect, 40 * 16, 130 * 16)

    # 'S' — "SAM" is unreadable at 16px, a single letter is not
    font = QFont("Segoe UI")
    font.setPixelSize(int(size * 0.42))
    font.setWeight(QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("#E8E8E8"))
    p.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")

    p.end()
    return pixmap


def main() -> int:
    app = QApplication(sys.argv)  # noqa: F841 — QPixmap needs a QApplication

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets = os.path.join(root, "assets")
    os.makedirs(assets, exist_ok=True)

    png_path = os.path.join(assets, "icon.png")
    ico_path = os.path.join(assets, "icon.ico")

    render_orb(RENDER_SIZE).save(png_path, "PNG")
    print(f"wrote {png_path}")

    try:
        from PIL import Image
    except ImportError:
        print("Pillow is required to write the .ico — pip install Pillow", file=sys.stderr)
        return 1

    image = Image.open(png_path).convert("RGBA")
    image.save(ico_path, format="ICO", sizes=[(s, s) for s in ICON_SIZES])
    print(f"wrote {ico_path} ({', '.join(str(s) for s in ICON_SIZES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
