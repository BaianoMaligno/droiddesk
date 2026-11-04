# DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
"""Complete Qt palettes: readable under both light and dark desktop themes."""
from pathlib import Path

from PyQt6.QtGui import QColor, QPalette


COLORS = {
    "dark": dict(bg="#111822", panel="#1b2533", alt="#202c3b", text="#e4ebf4", muted="#a4b3c6",
                 border="#35465b", hover="#2b3c51", selected="#294c73", accent="#78b5ff",
                 disabled="#263242", dim="#8a9bb0", header="#233143", sidebar="#0d141e"),
    "light": dict(bg="#f4f6f9", panel="#ffffff", alt="#f6f8fb", text="#253247", muted="#62748b",
                  border="#cbd6e3", hover="#eaf1fa", selected="#deebfb", accent="#2863a6",
                  disabled="#e9edf3", dim="#6c7c91", header="#edf2f8", sidebar="#202c3c"),
}


def stylesheet(theme):
    c = COLORS[theme]
    check = (Path(__file__).parent / "assets" / "check.svg").as_posix()
    arrow = (Path(__file__).parent / "assets" / "arrow.svg").as_posix()
    return f"""
QWidget {{ font-family:'Noto Sans','DejaVu Sans',sans-serif; font-size:13px; color:{c['text']}; }}
QMainWindow,QDialog,QMessageBox {{ background:{c['bg']}; }}
QFrame#sidebar {{ background:{c['sidebar']}; border:0; }}
QFrame#sidebar QLabel {{ color:#c7d5e8; }}
QLabel#brand {{ font-size:23px; font-weight:700; color:white; }}
QLabel#section {{ color:#9db0c9; font-size:10px; font-weight:700; }}
QLabel#heading {{ font-size:22px; font-weight:700; }}
QLabel#device {{ font-size:17px; font-weight:600; color:white; }}
QLabel#muted {{ color:{c['muted']}; }}
QListWidget#filters {{ background:transparent; border:0; outline:0; }}
QListWidget#filters::item {{ padding:12px 13px; border-radius:6px; margin:2px 0; color:#c7d3e3; }}
QListWidget#filters::item:selected {{ background:#315e91; color:white; font-weight:600; }}
QFrame#card,QFrame#inspector,QGroupBox {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:8px; }}
QGroupBox {{ margin-top:15px; padding-top:20px; }}
QGroupBox::title {{ subcontrol-origin:margin; left:14px; padding:0 5px; font-weight:600; }}
QScrollArea,QLabel#detailContent {{ background:{c['panel']}; color:{c['text']}; border:0; }}
QPushButton {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:5px; padding:8px 13px; }}
QPushButton:hover {{ background:{c['hover']}; border-color:{c['accent']}; }}
QPushButton:pressed {{ background:{c['selected']}; }}
QPushButton:disabled {{ background:{c['disabled']}; color:{c['dim']}; border-color:{c['border']}; }}
QPushButton#primary {{ background:#2f6db3; border-color:#4886cf; color:white; font-weight:600; }}
QPushButton#primary:hover {{ background:#377ecb; }}
QPushButton#primary:disabled {{ background:{c['disabled']}; border-color:{c['border']}; color:{c['dim']}; }}
QPushButton#danger {{ color:{'#ffb4b4' if theme == 'dark' else '#a92b35'}; border-color:{'#a94b55' if theme == 'dark' else '#c9838a'}; }}
QPushButton#danger:hover {{ background:{'#512d38' if theme == 'dark' else '#ffedef'}; }}
QPushButton#danger:disabled {{ color:{c['dim']}; border-color:{c['border']}; }}
QPushButton#quiet {{ background:transparent; border:0; color:{c['accent']}; padding:5px 7px; }}
QLineEdit,QComboBox {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:5px; padding:8px; selection-background-color:#376ba4; selection-color:white; }}
QLineEdit:focus,QComboBox:focus {{ border-color:{c['accent']}; }}
QComboBox {{ padding-right:27px; }}
QComboBox::drop-down {{ border:0; width:24px; }}
QComboBox::down-arrow {{ image:url("{arrow}"); width:12px; height:8px; }}
QComboBox QAbstractItemView,QMenu {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']}; selection-background-color:{c['selected']}; selection-color:{c['text']}; }}
QMenu::item {{ padding:8px 18px; }}
QMenu::item:selected {{ background:{c['selected']}; }}
QTabWidget::pane {{ border:0; }}
QTabBar::tab {{ background:transparent; color:{c['muted']}; padding:13px 19px; border-bottom:3px solid transparent; }}
QTabBar::tab:selected {{ color:{c['accent']}; border-bottom:3px solid {c['accent']}; font-weight:600; }}
QTableView,QListWidget {{ background:{c['panel']}; alternate-background-color:{c['alt']}; border:1px solid {c['border']}; gridline-color:{c['border']}; selection-background-color:{c['selected']}; selection-color:{c['text']}; outline:0; }}
QTableView::item {{ padding:4px 8px; border-bottom:1px solid {c['border']}; }}
QTableView::item:selected {{ background:{c['selected']}; }}
QHeaderView::section {{ background:{c['header']}; color:{c['muted']}; padding:10px 8px; border:0; border-bottom:1px solid {c['border']}; font-size:11px; font-weight:600; }}
QTableCornerButton::section {{ background:{c['header']}; border:0; }}
QPlainTextEdit {{ background:#101923; color:#cfdef0; border:1px solid {c['border']}; border-radius:6px; padding:10px; font-family:'DejaVu Sans Mono',monospace; font-size:12px; }}
QProgressBar {{ border:0; border-radius:3px; background:{c['border']}; height:5px; text-align:center; }}
QProgressBar::chunk {{ background:#5b9ce5; border-radius:3px; }}
QStatusBar {{ background:{c['header']}; }}
QCheckBox {{ spacing:8px; }}
QCheckBox::indicator,QTableView::indicator {{ width:16px; height:16px; border:1px solid {c['muted']}; border-radius:3px; background:{c['panel']}; }}
QCheckBox::indicator:checked,QTableView::indicator:checked {{ background:#3977be; border-color:#6ca8ef; image:url("{check}"); }}
QScrollBar:vertical {{ background:{c['panel']}; width:12px; margin:0; }}
QScrollBar::handle:vertical {{ background:{c['border']}; min-height:30px; border-radius:5px; margin:2px; }}
QScrollBar:horizontal {{ background:{c['panel']}; height:12px; margin:0; }}
QScrollBar::handle:horizontal {{ background:{c['border']}; min-width:30px; border-radius:5px; margin:2px; }}
QScrollBar::add-line,QScrollBar::sub-line {{ width:0; height:0; }}
QScrollBar::add-page,QScrollBar::sub-page {{ background:transparent; }}
QToolTip {{ background:{c['panel']}; color:{c['text']}; border:1px solid {c['border']}; padding:6px; }}
"""


LIGHT_STYLE = stylesheet("light")


def apply_theme(app, theme="dark"):
    c = COLORS[theme]
    palette = QPalette()
    values = dict(Window=c['bg'], WindowText=c['text'], Base=c['panel'], AlternateBase=c['alt'],
                  Text=c['text'], Button=c['panel'], ButtonText=c['text'], BrightText="#ffffff",
                  Highlight=c['selected'], HighlightedText=c['text'], PlaceholderText=c['muted'],
                  ToolTipBase=c['panel'], ToolTipText=c['text'], Link=c['accent'])
    for role, value in values.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(value))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(c['dim']))
    app.setProperty("darkTheme", theme == "dark")
    app.setPalette(palette)
    app.setStyleSheet(stylesheet(theme))
