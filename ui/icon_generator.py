# SAM — Runtime Tray Icon Generator
# QPainter ile runtime'da system tray ikonu olusturur.
# Harici .ico dosyasina gerek kalmaz.

from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon
from PyQt6.QtCore import Qt


def create_tray_icon() -> QIcon:
    """
    SAM icin system tray ikonu olusturur.
    Koyu arka plan uzerinde cyan 'S' harfi cizer.
    """
    SIZE = 64

    pixmap = QPixmap(SIZE, SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Arka plan — yuvarlak koyu kare
    painter.setBrush(QColor(10, 10, 15))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, SIZE, SIZE, 12, 12)

    # Ince cyan border
    border_color = QColor(0, 212, 170, 180)
    from PyQt6.QtGui import QPen
    painter.setPen(QPen(border_color, 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(2, 2, SIZE - 4, SIZE - 4, 10, 10)

    # 'S' harfi — cyan
    painter.setPen(QColor(0, 212, 170))
    font = QFont("Segoe UI", 36, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "S")

    painter.end()

    return QIcon(pixmap)
