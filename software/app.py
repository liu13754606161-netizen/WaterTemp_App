# -*- coding: utf-8 -*-
"""
RiverTemp-Reconstructor — 河流水温模拟与重建桌面软件

多模型（Air2Stream / 线性 / 季节线性 / 平衡温度 / 随机森林）水温重构，
差分进化参数率定，出版级可视化，结果一键导出。

说明：本文件开头部分曾因误操作被截断，现已依据其余完整代码与各模块接口重建。
"""

from __future__ import annotations

import os
import sys
import traceback

import matplotlib

matplotlib.use("Qt5Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core import prepare_series, results_to_dataframe
from model_comparison import (
    build_comparison_from_results,
    export_comparison_csv,
    metrics_summary_table,
    plot_nse_bar,
    plot_rmse_bar,
    plot_scatter_comparison,
    plot_time_series_comparison,
    save_comparison_figures,
)
from model_training import (
    count_trained,
    empty_model_results,
    is_trained,
    train_model,
    trained_model_keys,
)
from models.model_catalog import (
    ALL_MODEL_KEYS,
    GUI_MODEL_LABELS,
    MODEL_KEY_TO_LABEL,
    get_catalog,
    get_model_key,
)
from ui.formula_panel import FormulaPanel

# 中文字体，避免图表中文显示为方块
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(APP_DIR, "startup_error.log")


def _show_fatal(title: str, message: str) -> None:
    """启动失败时弹窗并写入日志，避免窗口闪退看不到报错。"""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(message)
    except Exception:
        pass
    try:
        from ctypes import windll

        windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def _sample_path() -> str:
    return os.path.join(APP_DIR, "示例数据.csv")


class MetricCard(QFrame):
    """大数字指标卡片（对应网页版 st.metric）。"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "MetricCard{background:#f8fafc;border:1px solid #e2e8f0;"
            "border-radius:8px;padding:6px;}"
        )
        layout = QVBoxLayout(self)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color:#5f6368;font-size:11px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(
            "color:#1a73e8;font-size:22px;font-weight:bold;"
        )
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, text: str) -> None:
        self.value_label.setText(str(text))


class ModelTrainThread(QThread):
    """在后台线程训练模型，避免阻塞界面。"""

    train_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        data_dict: dict,
        model_key: str,
        popsize: int = 15,
        maxiter: int = 100,
        tol: float = 0.01,
        parent=None,
    ):
        super().__init__(parent)
        self.data_dict = data_dict
        self.model_key = model_key
        self.popsize = popsize
        self.maxiter = maxiter
        self.tol = tol

    def run(self):
        try:
            entry = train_model(
                self.model_key,
                self.data_dict,
                popsize=self.popsize,
                maxiter=self.maxiter,
                tol=self.tol,
            )
            self.train_completed.emit(entry)
        except Exception as exc:
            self.error_occurred.emit(f"{type(exc).__name__}: {exc}")


class ChartPanel(QWidget):
    """带导航工具栏的 matplotlib 图表面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(8, 4.5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    def clear(self) -> None:
        self.figure.clear()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiverTemp-Reconstructor — 河流水温模拟与重建")
        self.resize(1280, 860)
        self.setFont(QFont("Microsoft YaHei", 10))

        # 运行期状态
        self.data: pd.DataFrame | None = None
        self.data_dict: dict | None = None
        self.model_results = empty_model_results()
        self.comparison_results: dict | None = None
        self.train_thread: ModelTrainThread | None = None
        self._last_train_elapsed = 0.0

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("就绪 — 请先在数据导入页加载数据")

        self.create_import_tab()
        self.create_calibration_tab()
        self.create_visualization_tab()
        self.create_export_tab()

        # 初始化公式面板（模型下拉已在 create_calibration_tab 中填充，此处不要重复填充，
        # 否则在信号已连接时再次 clear/addItem 会导致重入崩溃）
        self._on_model_selection_changed()

    # ─── 特性 1：数据导入与列名映射 ──────────────────────────
    def create_import_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        group = QGroupBox("数据导入与列名映射")
        gl = QVBoxLayout()

        title = QLabel("导入包含时间、气温（Ta）、水温（Tw）的 CSV 文件")
        title.setStyleSheet("font-size:12px;color:#3c5470;font-weight:bold;")
        gl.addWidget(title)

        btn_row = QHBoxLayout()
        self.file_btn = QPushButton("📂 选择 CSV 文件")
        self.file_btn.clicked.connect(self.select_file)
        sample_btn = QPushButton("📋 加载内置示例数据")
        sample_btn.setStyleSheet("background: #5f6368;")
        sample_btn.clicked.connect(self.load_sample)
        btn_row.addWidget(self.file_btn)
        btn_row.addWidget(sample_btn)
        btn_row.addStretch()
        gl.addLayout(btn_row)

        self.file_label = QLabel("未选择文件")
        self.file_label.setWordWrap(True)
        gl.addWidget(self.file_label)

        map_row = QHBoxLayout()
        map_row.addWidget(QLabel("日期列 (Date):"))
        self.date_combo = QComboBox()
        self.date_combo.setMinimumWidth(140)
        map_row.addWidget(self.date_combo)
        map_row.addWidget(QLabel("实测气温 (Ta):"))
        self.ta_combo = QComboBox()
        self.ta_combo.setMinimumWidth(140)
        map_row.addWidget(self.ta_combo)
        map_row.addWidget(QLabel("实测水温 (Tw):"))
        self.tw_combo = QComboBox()
        self.tw_combo.setMinimumWidth(140)
        map_row.addWidget(self.tw_combo)
        map_row.addStretch()
        gl.addLayout(map_row)

        gl.addWidget(QLabel("数据预览（前 5 行，确认映射前请检查）："))
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        gl.addWidget(self.data_table)

        self.mapping_info = QLabel("")
        self.mapping_info.setStyleSheet("color: #137333;")
        gl.addWidget(self.mapping_info)

        self.confirm_btn = QPushButton("✅ 确认列名映射")
        self.confirm_btn.clicked.connect(self.confirm_mapping)
        self.confirm_btn.setEnabled(False)
        gl.addWidget(self.confirm_btn)

        group.setLayout(gl)
        layout.addWidget(group)
        self.tabs.addTab(tab, "📂 数据导入")

    # ─── 特性 2：模型训练与比较 ───────────────────────────────
    def create_calibration_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        tab = QWidget()
        layout = QVBoxLayout(tab)

        settings_group = QGroupBox("模型设置")
        sg = QVBoxLayout()
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("模型选择："))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(240)
        self._init_model_combo()
        self.model_combo.currentIndexChanged.connect(self._on_model_selection_changed)
        model_row.addWidget(self.model_combo)
        self.trained_summary_label = QLabel("")
        self.trained_summary_label.setStyleSheet("color: #5f6368; font-size: 11px;")
        model_row.addWidget(self.trained_summary_label)
        model_row.addStretch()
        sg.addLayout(model_row)
        settings_group.setLayout(sg)
        layout.addWidget(settings_group)

        formula_group = QGroupBox("模型公式")
        fg = QVBoxLayout()
        self.formula_panel = FormulaPanel()
        self.formula_panel.setMinimumHeight(120)
        fg.addWidget(self.formula_panel)
        formula_group.setLayout(fg)
        layout.addWidget(formula_group)

        spec_group = QGroupBox("参数说明")
        sp = QVBoxLayout()
        self.param_spec_table = QTableWidget()
        self.param_spec_table.setColumnCount(4)
        self.param_spec_table.setHorizontalHeaderLabels(["参数名称", "物理意义", "单位", "取值范围"])
        self.param_spec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.param_spec_table.setMaximumHeight(160)
        sp.addWidget(self.param_spec_table)
        self.model_desc_browser = QTextBrowser()
        self.model_desc_browser.setMaximumHeight(72)
        sp.addWidget(self.model_desc_browser)
        spec_group.setLayout(sp)
        layout.addWidget(spec_group)

        train_group = QGroupBox("模型训练")
        tl = QVBoxLayout()

        self.de_param_widget = QWidget()
        de_pl = QHBoxLayout(self.de_param_widget)
        p1 = QVBoxLayout()
        p1.addWidget(QLabel("种群规模 (popsize)"))
        self.popsize_spin = QSpinBox()
        self.popsize_spin.setRange(5, 50)
        self.popsize_spin.setValue(15)
        p1.addWidget(self.popsize_spin)
        p2 = QVBoxLayout()
        p2.addWidget(QLabel("最大迭代 (maxiter)"))
        self.maxiter_spin = QSpinBox()
        self.maxiter_spin.setRange(10, 500)
        self.maxiter_spin.setValue(100)
        p2.addWidget(self.maxiter_spin)
        p3 = QVBoxLayout()
        p3.addWidget(QLabel("收敛阈值 (tol)"))
        self.tol_spin = QDoubleSpinBox()
        self.tol_spin.setRange(0.001, 1.0)
        self.tol_spin.setValue(0.01)
        self.tol_spin.setSingleStep(0.005)
        p3.addWidget(self.tol_spin)
        de_pl.addLayout(p1)
        de_pl.addLayout(p2)
        de_pl.addLayout(p3)
        de_pl.addStretch()
        tl.addWidget(self.de_param_widget)

        btn_row = QHBoxLayout()
        self.train_btn = QPushButton("开始模型训练")
        self.train_btn.clicked.connect(self.start_model_training)
        self.train_btn.setEnabled(False)
        btn_row.addWidget(self.train_btn)
        self.save_train_btn = QPushButton("保存训练结果")
        self.save_train_btn.clicked.connect(self.save_training_result)
        self.save_train_btn.setEnabled(False)
        btn_row.addWidget(self.save_train_btn)
        btn_row.addStretch()
        tl.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat("模型训练中...")
        tl.addWidget(self.progress_bar)

        self.status_label = QLabel("就绪 — 请先完成数据映射")
        tl.addWidget(self.status_label)

        cards = QHBoxLayout()
        self.card_rmse = MetricCard("RMSE")
        self.card_nse = MetricCard("NSE")
        self.card_r2 = MetricCard("R²")
        self.card_mae = MetricCard("MAE")
        for c in (self.card_rmse, self.card_nse, self.card_r2, self.card_mae):
            cards.addWidget(c)
        tl.addLayout(cards)

        tl.addWidget(QLabel("训练得到的参数值："))
        self.fitted_params_table = QTableWidget()
        self.fitted_params_table.setColumnCount(2)
        self.fitted_params_table.setHorizontalHeaderLabels(["参数", "数值"])
        self.fitted_params_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fitted_params_table.setMaximumHeight(140)
        tl.addWidget(self.fitted_params_table)
        train_group.setLayout(tl)
        layout.addWidget(train_group)

        cmp_group = QGroupBox("模型比较（与训练独立，可任选已训练模型）")
        cgl = QVBoxLayout()
        cgl.addWidget(QLabel("勾选参与比较的模型（至少 2 个已训练）："))
        self.compare_checks: dict[str, QCheckBox] = {}
        checks_wrap = QVBoxLayout()
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        for i, label in enumerate(GUI_MODEL_LABELS):
            key = get_model_key(label)
            cb = QCheckBox(label)
            cb.setEnabled(False)
            cb.stateChanged.connect(self._update_compare_button)
            self.compare_checks[key] = cb
            (row1 if i < 3 else row2).addWidget(cb)
        checks_wrap.addLayout(row1)
        checks_wrap.addLayout(row2)
        cgl.addLayout(checks_wrap)

        cmp_btn_row = QHBoxLayout()
        select_trained_btn = QPushButton("勾选全部已训练")
        select_trained_btn.setStyleSheet("background: #5f6368;")
        select_trained_btn.clicked.connect(self._select_all_trained_for_compare)
        cmp_btn_row.addWidget(select_trained_btn)
        clear_cmp_btn = QPushButton("取消全选")
        clear_cmp_btn.setStyleSheet("background: #5f6368;")
        clear_cmp_btn.clicked.connect(self._clear_compare_selection)
        cmp_btn_row.addWidget(clear_cmp_btn)
        cmp_btn_row.addStretch()
        cgl.addLayout(cmp_btn_row)

        self.compare_btn = QPushButton("模型比较")
        self.compare_btn.setStyleSheet("background: #34a853;")
        self.compare_btn.clicked.connect(self.start_comparison)
        self.compare_btn.setEnabled(False)
        cgl.addWidget(self.compare_btn)
        cgl.addWidget(QLabel("比较结果（按 RMSE 升序）："))
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(5)
        self.comparison_table.setHorizontalHeaderLabels(["模型", "RMSE", "MAE", "R²", "NSE"])
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comparison_table.setMaximumHeight(180)
        cgl.addWidget(self.comparison_table)
        cmp_group.setLayout(cgl)
        layout.addWidget(cmp_group)
        layout.addStretch()

        scroll.setWidget(tab)
        self.tabs.addTab(scroll, "🔬 模型训练")

    # ─── 特性 3：专业可视化 ───────────────────────────────────
    def create_visualization_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        group = QGroupBox("结果可视化")
        gl = QVBoxLayout()

        self.chart_tabs = QTabWidget()
        self.ts_panel = ChartPanel()
        self.scatter_panel = ChartPanel()
        self.cmp_ts_panel = ChartPanel()
        self.cmp_scatter_panel = ChartPanel()
        self.cmp_rmse_panel = ChartPanel()
        self.cmp_nse_panel = ChartPanel()
        self.chart_tabs.addTab(self.ts_panel, "📈 当前模型时间序列")
        self.chart_tabs.addTab(self.scatter_panel, "🎯 当前模型散点图")
        self.chart_tabs.addTab(self.cmp_ts_panel, "📈 多模型时间序列")
        self.chart_tabs.addTab(self.cmp_scatter_panel, "🎯 多模型散点图")
        self.chart_tabs.addTab(self.cmp_rmse_panel, "📊 RMSE 柱状图")
        self.chart_tabs.addTab(self.cmp_nse_panel, "📊 NSE 柱状图")
        gl.addWidget(self.chart_tabs)

        hint = QLabel("提示：可使用图表上方工具栏缩放、平移、保存图片。")
        hint.setStyleSheet("color: #5f6368; font-size: 11px;")
        gl.addWidget(hint)

        group.setLayout(gl)
        layout.addWidget(group)
        self.tabs.addTab(tab, "📊 结果可视化")

    # ─── 结果导出 ─────────────────────────────────────────────
    def create_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        group = QGroupBox("结果导出")
        gl = QVBoxLayout()

        gl.addWidget(QLabel("率定结果预览（前 10 行）："))
        self.export_table = QTableWidget()
        self.export_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        gl.addWidget(self.export_table)

        self.export_btn = QPushButton("⬇️ 导出结果 CSV")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        gl.addWidget(self.export_btn)

        self.export_cmp_btn = QPushButton("⬇️ 导出模型比较 CSV / PNG")
        self.export_cmp_btn.clicked.connect(self.export_comparison)
        self.export_cmp_btn.setEnabled(False)
        gl.addWidget(self.export_cmp_btn)

        group.setLayout(gl)
        layout.addWidget(group)
        self.tabs.addTab(tab, "💾 结果导出")

    # ─── 数据操作 ─────────────────────────────────────────────
    def _fill_table(self, table: QTableWidget, df: pd.DataFrame):
        table.setRowCount(len(df))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for i, row in df.iterrows():
            for j, value in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(value)))

    def _populate_combos(self):
        self.date_combo.clear()
        self.ta_combo.clear()
        self.tw_combo.clear()
        for col in self.data.columns:
            col_s = str(col)
            self.date_combo.addItem(col_s)
            self.ta_combo.addItem(col_s)
            self.tw_combo.addItem(col_s)
        if len(self.data.columns) >= 3:
            self.ta_combo.setCurrentIndex(1)
            self.tw_combo.setCurrentIndex(2)

    def load_dataframe(self, df: pd.DataFrame, label: str):
        self.data = df
        self.file_label.setText(f"已加载：{label}  （共 {len(df)} 行 × {len(df.columns)} 列）")
        self._populate_combos()
        self._fill_table(self.data_table, df.head(5))
        self.confirm_btn.setEnabled(True)
        self.data_dict = None
        self.model_results = empty_model_results()
        self.comparison_results = None
        self.train_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)
        self.save_train_btn.setEnabled(False)
        self.mapping_info.setText("")
        self.export_btn.setEnabled(False)
        self.export_cmp_btn.setEnabled(False)
        self.comparison_table.setRowCount(0)
        self._clear_metrics()
        self._refresh_model_combo()
        self._refresh_compare_checks()
        self._update_compare_button()
        self._update_status_bar()
        self.statusBar().showMessage("数据已加载，请确认列名映射")

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 CSV 文件", APP_DIR, "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            self.load_dataframe(pd.read_csv(path, encoding="utf-8-sig"), path)
        except UnicodeDecodeError:
            self.load_dataframe(pd.read_csv(path, encoding="gbk"), path)
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"加载失败：{exc}")

    def load_sample(self):
        path = _sample_path()
        if not os.path.isfile(path):
            QMessageBox.warning(self, "提示", f"未找到示例文件：\n{path}")
            return
        try:
            self.load_dataframe(pd.read_csv(path, encoding="utf-8-sig"), "示例数据.csv")
        except Exception as exc:
            QMessageBox.critical(self, "错误", f"加载示例失败：{exc}")

    def confirm_mapping(self):
        if self.data is None:
            return
        try:
            self.data_dict = prepare_series(
                self.data,
                self.date_combo.currentText(),
                self.ta_combo.currentText(),
                self.tw_combo.currentText(),
            )
            n = len(self.data_dict["Tw"])
            d0 = self.data_dict["dates"].min().strftime("%Y-%m-%d")
            d1 = self.data_dict["dates"].max().strftime("%Y-%m-%d")
            self.mapping_info.setText(f"✓ 映射成功：有效记录 {n} 条，时间范围 {d0} — {d1}")
            self.train_btn.setEnabled(True)
            self.status_label.setText(f"已就绪，共 {n} 条有效数据 — 请依次训练各模型")
            QMessageBox.information(self, "成功", f"列名映射已确认！\n有效记录：{n} 条")
            self.tabs.setCurrentIndex(1)
            self._refresh_compare_checks()
            self._update_compare_button()
            self._update_status_bar()
            self.statusBar().showMessage("可以开始模型训练")
        except Exception as exc:
            self.mapping_info.setText("")
            QMessageBox.warning(self, "映射失败", str(exc))

    # ─── 模型信息与训练 ───────────────────────────────────────
    def _init_model_combo(self) -> None:
        self.model_combo.clear()
        for label in GUI_MODEL_LABELS:
            self.model_combo.addItem(label, get_model_key(label))

    def _refresh_model_combo(self, keep_key: str | None = None) -> None:
        if keep_key is None:
            keep_key = self._current_model_key()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for label in GUI_MODEL_LABELS:
            key = get_model_key(label)
            text = label
            if is_trained(self.model_results, key):
                text += "  [已训练]"
            self.model_combo.addItem(text, key)
        idx = self.model_combo.findData(keep_key)
        self.model_combo.setCurrentIndex(max(idx, 0))
        self.model_combo.blockSignals(False)
        n = count_trained(self.model_results)
        self.trained_summary_label.setText(f"已训练 {n}/{len(ALL_MODEL_KEYS)} 个")

    def _current_model_key(self) -> str:
        data = self.model_combo.currentData()
        if data is not None:
            return str(data)
        text = self.model_combo.currentText().split("  [")[0].strip()
        return get_model_key(text)

    def _refresh_compare_checks(self) -> None:
        for key, cb in self.compare_checks.items():
            trained = is_trained(self.model_results, key)
            cb.blockSignals(True)
            cb.setEnabled(trained)
            if not trained:
                cb.setChecked(False)
            cb.blockSignals(False)
            cb.setToolTip("可参与比较" if trained else "请先在上方训练此模型")

    def _get_selected_compare_keys(self) -> list[str]:
        return [k for k, cb in self.compare_checks.items() if cb.isChecked()]

    def _select_all_trained_for_compare(self) -> None:
        for key, cb in self.compare_checks.items():
            if is_trained(self.model_results, key):
                cb.setChecked(True)
        self._update_compare_button()

    def _clear_compare_selection(self) -> None:
        for cb in self.compare_checks.values():
            cb.setChecked(False)
        self._update_compare_button()

    def _on_model_selection_changed(self):
        key = self._current_model_key()
        catalog = get_catalog(key)
        self.formula_panel.show_model(catalog)

        params = catalog["params"]
        self.param_spec_table.setRowCount(len(params))
        for i, (name, meaning, unit, rng) in enumerate(params):
            self.param_spec_table.setItem(i, 0, QTableWidgetItem(name))
            self.param_spec_table.setItem(i, 1, QTableWidgetItem(meaning))
            self.param_spec_table.setItem(i, 2, QTableWidgetItem(unit))
            self.param_spec_table.setItem(i, 3, QTableWidgetItem(rng))

        self.model_desc_browser.setPlainText(
            f"{catalog['description']}\n\n训练方法：{catalog['method']}"
        )
        self.de_param_widget.setVisible(key == "Air2Stream")

        entry = self.model_results.get(key)
        if entry and entry.get("trained"):
            self._show_training_metrics(entry)
            self.status_label.setText(
                f"{catalog['title']} — 已训练（RMSE={entry['metrics']['RMSE']:.4f}），可保存或参与比较"
            )
            self.save_train_btn.setEnabled(True)
        else:
            self._clear_metrics()
            self.save_train_btn.setEnabled(False)
            self.status_label.setText(f"{catalog['title']} — 尚未训练，请点击「开始模型训练」")

        self._update_status_bar()
        self._update_compare_button()

    def _update_status_bar(self):
        label = MODEL_KEY_TO_LABEL.get(self._current_model_key(), self.model_combo.currentText())
        key = self._current_model_key()
        trained = is_trained(self.model_results, key)
        status = "已训练" if trained else "未训练"
        elapsed = ""
        entry = self.model_results.get(key)
        if entry and entry.get("trained"):
            elapsed = f" | 训练耗时：{entry['elapsed_sec']:.1f}秒"
        n = count_trained(self.model_results)
        self.statusBar().showMessage(
            f"当前模型：{label} | 训练状态：{status}{elapsed} | 已累计训练 {n}/{len(ALL_MODEL_KEYS)} 个模型"
        )

    def _update_compare_button(self):
        if self.data_dict is None:
            self.compare_btn.setEnabled(False)
            return
        trained_selected = [
            k for k in self._get_selected_compare_keys() if is_trained(self.model_results, k)
        ]
        self.compare_btn.setEnabled(len(trained_selected) >= 2)

    def start_model_training(self):
        if self.data_dict is None:
            QMessageBox.warning(self, "提示", "请先在「数据导入」页确认列名映射")
            return

        model_key = self._current_model_key()
        label = self.model_combo.currentText()

        self.train_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"正在训练 {label} ...")
        self.statusBar().showMessage(f"{label} 训练中...")

        self.train_thread = ModelTrainThread(
            self.data_dict,
            model_key,
            self.popsize_spin.value(),
            self.maxiter_spin.value(),
            self.tol_spin.value(),
        )
        self.train_thread.train_completed.connect(self.on_train_completed)
        self.train_thread.error_occurred.connect(self.on_train_error)
        self.train_thread.start()

    def on_train_completed(self, entry: dict):
        key = entry["model_key"]
        self.model_results[key] = entry
        self._last_train_elapsed = entry["elapsed_sec"]

        self._show_training_metrics(entry)
        self.save_train_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

        plot_result = self._entry_to_plot_result(entry)
        self.plot_time_series(plot_result)
        self.plot_scatter(plot_result)
        self._fill_export_preview(entry)

        self.progress_bar.setVisible(False)
        self.status_label.setText(
            f"{self.model_combo.currentText()} 训练完成（耗时 {entry['elapsed_sec']:.1f} 秒）"
        )
        self.train_btn.setEnabled(True)
        if key in self.compare_checks:
            self.compare_checks[key].blockSignals(True)
            self.compare_checks[key].setEnabled(True)
            self.compare_checks[key].setChecked(True)
            self.compare_checks[key].blockSignals(False)
        self._refresh_model_combo(keep_key=key)
        self._on_model_selection_changed()
        self._update_compare_button()
        self._update_status_bar()

    def on_train_error(self, error: str):
        QMessageBox.critical(self, "训练失败", error)
        self.progress_bar.setVisible(False)
        self.status_label.setText("训练失败，请检查数据或参数设置")
        self.train_btn.setEnabled(True)
        self._update_compare_button()
        self._update_status_bar()

    def _show_training_metrics(self, entry: dict):
        metrics = entry["metrics"]
        self.card_rmse.set_value(f"{metrics['RMSE']:.4f}")
        self.card_nse.set_value(f"{metrics['NSE']:.4f}")
        self.card_r2.set_value(f"{metrics['R2']:.4f}")
        self.card_mae.set_value(f"{metrics['MAE']:.4f}")

        params = entry.get("params", {})
        self.fitted_params_table.setRowCount(len(params))
        for i, (k, v) in enumerate(params.items()):
            self.fitted_params_table.setItem(i, 0, QTableWidgetItem(str(k)))
            self.fitted_params_table.setItem(i, 1, QTableWidgetItem(f"{float(v):.6f}"))

    def _clear_metrics(self):
        for card in (self.card_rmse, self.card_nse, self.card_r2, self.card_mae):
            card.set_value("--")
        self.fitted_params_table.setRowCount(0)

    def _entry_to_plot_result(self, entry: dict) -> dict:
        return {
            "Tw_sim": entry["Tw_pred"],
            "metrics": entry["metrics"],
        }

    def save_training_result(self):
        key = self._current_model_key()
        entry = self.model_results.get(key)
        if not entry or not entry.get("trained"):
            QMessageBox.information(self, "提示", "请先完成当前模型的训练")
            return

        label = self.model_combo.currentText().replace(" ", "_")
        default = os.path.join(APP_DIR, f"RiverTemp_{label}_training.csv")
        path, _ = QFileDialog.getSaveFileName(self, "保存训练结果", default, "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            rows = [{"参数": k, "数值": v} for k, v in entry["params"].items()]
            for mk, mv in entry["metrics"].items():
                rows.append({"参数": mk, "数值": mv})
            pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")

            if entry.get("calibration_result") and self.data_dict:
                series_path = path.replace(".csv", "_series.csv")
                results_to_dataframe(self.data_dict, entry["calibration_result"]).to_csv(
                    series_path, index=False, encoding="utf-8-sig"
                )
                QMessageBox.information(
                    self, "成功", f"参数与指标：\n{path}\n时间序列：\n{series_path}"
                )
            else:
                QMessageBox.information(self, "成功", f"训练结果已保存：\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))

    def start_comparison(self):
        selected = self._get_selected_compare_keys()
        trained_selected = [k for k in selected if is_trained(self.model_results, k)]

        if len(trained_selected) < 2:
            trained = trained_model_keys(self.model_results)
            if len(trained) < 2:
                QMessageBox.warning(
                    self,
                    "提示",
                    "至少需要 2 个已训练的模型才能比较。\n请先对多个模型分别点击「开始模型训练」。",
                )
            else:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请在下方的比较列表中勾选至少 2 个已训练的模型。",
                )
            return

        try:
            result = build_comparison_from_results(
                self.model_results,
                self.data_dict,
                selected_keys=trained_selected,
            )
        except Exception as exc:
            QMessageBox.critical(self, "模型比较失败", str(exc))
            return

        self.comparison_results = result
        summary = metrics_summary_table(result["metrics_df"])

        self.comparison_table.setRowCount(len(summary))
        for i, row in summary.iterrows():
            self.comparison_table.setItem(i, 0, QTableWidgetItem(str(row["模型"])))
            self.comparison_table.setItem(i, 1, QTableWidgetItem(f"{row['RMSE']:.4f}"))
            self.comparison_table.setItem(i, 2, QTableWidgetItem(f"{row['MAE']:.4f}"))
            self.comparison_table.setItem(i, 3, QTableWidgetItem(f"{row['R²']:.4f}"))
            self.comparison_table.setItem(i, 4, QTableWidgetItem(f"{row['NSE']:.4f}"))

        self._plot_comparison_charts(result)
        self._auto_export_comparison(result)

        self.export_cmp_btn.setEnabled(True)
        self.status_label.setText("模型比较完成！图表与 CSV 已生成")
        self.tabs.setCurrentIndex(2)
        self.chart_tabs.setCurrentIndex(2)
        self.statusBar().showMessage("多模型比较完成")

    def _plot_comparison_charts(self, result: dict):
        for panel, plot_fn in (
            (self.cmp_ts_panel, plot_time_series_comparison),
            (self.cmp_scatter_panel, plot_scatter_comparison),
        ):
            panel.clear()
            ax = panel.figure.add_subplot(111)
            plot_fn(result, ax=ax)
            panel.figure.tight_layout()
            panel.canvas.draw()

        self.cmp_rmse_panel.clear()
        ax_rmse = self.cmp_rmse_panel.figure.add_subplot(111)
        plot_rmse_bar(result, ax=ax_rmse)
        self.cmp_rmse_panel.canvas.draw()

        self.cmp_nse_panel.clear()
        ax_nse = self.cmp_nse_panel.figure.add_subplot(111)
        plot_nse_bar(result, ax=ax_nse)
        self.cmp_nse_panel.canvas.draw()

    def _auto_export_comparison(self, result: dict):
        csv_path = os.path.join(APP_DIR, "model_comparison.csv")
        export_comparison_csv(result, csv_path)
        save_comparison_figures(result, APP_DIR)

    def export_comparison(self):
        if not self.comparison_results:
            QMessageBox.information(self, "提示", "请先运行「模型比较」")
            return
        default = os.path.join(APP_DIR, "model_comparison.csv")
        path, _ = QFileDialog.getSaveFileName(self, "保存模型比较结果", default, "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            export_comparison_csv(self.comparison_results, path)
            out_dir = os.path.dirname(path) or APP_DIR
            paths = save_comparison_figures(self.comparison_results, out_dir)
            QMessageBox.information(
                self,
                "成功",
                f"比较结果已保存：\n{path}\n\n图片：\n" + "\n".join(paths.values()),
            )
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))

    # ─── 绘图 ─────────────────────────────────────────────────
    def plot_time_series(self, result: dict):
        panel = self.ts_panel
        panel.clear()
        ax = panel.figure.add_subplot(111)

        dates = self.data_dict["dates"]
        tw_obs = self.data_dict["Tw"]
        tw_sim = result["Tw_sim"]

        ax.plot(dates, tw_obs, color="#1f77b4", linewidth=2, label="实测水温")
        ax.plot(dates, tw_sim, color="#d62728", linewidth=2, linestyle="--", label="模拟水温")
        ax.set_title("水温时间序列对比（实测 vs 模拟）", fontsize=13, pad=12)
        ax.set_xlabel("日期")
        ax.set_ylabel("水温 (°C)")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        panel.figure.autofmt_xdate()
        panel.figure.tight_layout()
        panel.canvas.draw()

    def plot_scatter(self, result: dict):
        panel = self.scatter_panel
        panel.clear()
        ax = panel.figure.add_subplot(111)

        tw_obs = self.data_dict["Tw"]
        tw_sim = result["Tw_sim"]
        r2 = result["metrics"]["R2"]

        ax.scatter(tw_obs, tw_sim, c="#2ca02c", alpha=0.65, s=36, edgecolors="white", linewidths=0.5)
        lo = float(min(tw_obs.min(), tw_sim.min()))
        hi = float(max(tw_obs.max(), tw_sim.max()))
        pad = (hi - lo) * 0.05 or 1.0
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color="#ff7f0e", linestyle="--", linewidth=2, label="1:1 参考线")
        ax.set_title(f"模拟 vs 实测散点图（R² = {r2:.4f}）", fontsize=13, pad=12)
        ax.set_xlabel("实测水温 (°C)")
        ax.set_ylabel("模拟水温 (°C)")
        ax.set_aspect("equal", adjustable="box")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.3)
        panel.figure.tight_layout()
        panel.canvas.draw()

    def _fill_export_preview(self, entry: dict | None = None):
        if not self.data_dict:
            return
        key = self._current_model_key()
        entry = entry or self.model_results.get(key)
        if not entry or not entry.get("trained"):
            return
        if entry.get("calibration_result"):
            df = results_to_dataframe(self.data_dict, entry["calibration_result"])
        else:
            df = pd.DataFrame(
                {
                    "Date": self.data_dict["dates"].dt.strftime("%Y-%m-%d"),
                    "Observed_Tw": self.data_dict["Tw"],
                    "Predicted_Tw": entry["Tw_pred"],
                    "Residual": entry["Tw_pred"] - self.data_dict["Tw"],
                }
            )
        self._fill_table(self.export_table, df.head(10))

    def export_results(self):
        key = self._current_model_key()
        entry = self.model_results.get(key)
        if not entry or not entry.get("trained") or not self.data_dict:
            QMessageBox.information(self, "提示", "请先完成当前模型训练")
            return

        label = self.model_combo.currentText().replace(" ", "_")
        default = os.path.join(APP_DIR, f"RiverTemp_{label}_series.csv")
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", default, "CSV 文件 (*.csv)")
        if not path:
            return
        try:
            if entry.get("calibration_result"):
                results_to_dataframe(self.data_dict, entry["calibration_result"]).to_csv(
                    path, index=False, encoding="utf-8-sig"
                )
            else:
                pd.DataFrame(
                    {
                        "Date": self.data_dict["dates"].dt.strftime("%Y-%m-%d"),
                        "Observed_Tw": self.data_dict["Tw"],
                        "Predicted_Tw": entry["Tw_pred"],
                        "Residual": entry["Tw_pred"] - self.data_dict["Tw"],
                    }
                ).to_csv(path, index=False, encoding="utf-8-sig")
            QMessageBox.information(self, "成功", f"结果已保存：\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))


def main():
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("RiverTemp-Reconstructor")
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception:
        _show_fatal("RiverTemp 启动失败", traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
