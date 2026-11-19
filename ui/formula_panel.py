# -*- coding: utf-8 -*-

from __future__ import annotations

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QVBoxLayout, QWidget


class FormulaPanel(QWidget):
    """使用 matplotlib mathtext 渲染 LaTeX 公式。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(8, 1.6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def show_model(self, catalog: dict) -> None:
        self.figure.clear()
        title = catalog.get("title", "")
        if title:
            self.figure.text(0.5, 0.92, title, ha="center", va="top", fontsize=11, weight="bold")

        if catalog.get("show_formula", True) and catalog.get("latex"):
            latex = catalog["latex"]
            if "\n" in latex:
                lines = [ln.strip() for ln in latex.split("\n") if ln.strip()]
                y0 = 0.55
                step = 0.28 / max(len(lines), 1)
                for i, line in enumerate(lines):
                    self.figure.text(0.5, y0 - i * step, line, ha="center", va="center", fontsize=12)
            else:
                self.figure.text(0.5, 0.45, latex, ha="center", va="center", fontsize=13)
        elif catalog.get("plain_formula"):
            text = catalog["plain_formula"]
            self.figure.text(
                0.5,
                0.45,
                text,
                ha="center",
                va="center",
                fontsize=10,
                family="Microsoft YaHei",
            )

        ax = self.figure.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        # self.figure.tight_layout(pad=0.5)  # 移除tight_layout以避免警告
        self.canvas.draw()
