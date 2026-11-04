# DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
from __future__ import annotations

import base64
import csv
import json
import shlex
import shutil
import subprocess
import sys
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QObject, QRunnable, QThreadPool, pyqtSignal, QTimer, QProcess, QEvent, QSettings
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QKeySequence, QShortcut, QPalette
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QComboBox, QListWidget, QListWidgetItem, QTableView, QHeaderView, QAbstractItemView,
    QSplitter, QTabWidget, QPlainTextEdit, QProgressBar, QCheckBox, QFileDialog, QMessageBox, QDialog,
    QDialogButtonBox, QTableWidget, QTableWidgetItem, QMenu, QInputDialog, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QGroupBox, QScrollArea)

from adb_backend import Adb, AdbError, Package, Snapshot, Outcome, CACHE, ROOT, read_preset

from version import VERSION, CREATOR, COAUTHOR
FILTERS = [("enabled", 'Active'), ("system", "System"), ("user", 'User'), ("disabled", 'Disabled'), ("removed", 'Removed'), ("all", "All")]
OPERATIONS = [('Disable', "disable"), ('Reactivate', "enable"), ('Restore', "restore"), ('Export APKs', "export"), ('Uninstall for this user', "uninstall")]
from themes import LIGHT_STYLE as STYLE, apply_theme



def button(text, fn, primary=False, quiet=False):
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary: b.setObjectName("primary")
    if quiet: b.setObjectName("quiet")
    b.clicked.connect(fn)
    return b


def label(text="", name="", wrap=False):
    w = QLabel(text)
    if name: w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


class Signals(QObject):
    done = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)
    log = pyqtSignal(str)


class Task(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = Signals()

    def run(self):
        try:
            self.signals.done.emit(self.fn(self.signals.progress.emit, self.signals.log.emit))
        except Exception as exc:
            self.signals.log.emit(traceback.format_exc())
            self.signals.error.emit(str(exc))


class PackageModel(QAbstractTableModel):
    marked = pyqtSignal()
    HEADERS = ["", 'APP / PACKAGE', "TIPO", 'STATE', 'VERSION', "APKs"]

    def __init__(self):
        super().__init__()
        self.rows: list[Package] = []
        self.checked: set[str] = set()
        self.icons: dict[str, QIcon] = {}

    def set_packages(self, packages):
        self.beginResetModel()
        self.rows = packages
        self.checked.intersection_update(p.name for p in packages)
        for p in packages:
            if p.icon:
                pixmap = QPixmap()
                if pixmap.loadFromData(base64.b64decode(p.icon)):
                    self.icons[p.name] = QIcon(pixmap)
        self.endResetModel()
        self.marked.emit()

    def rowCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.rows)
    def columnCount(self, parent=QModelIndex()): return 6
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        p, c = self.rows[index.row()], index.column()
        if role == Qt.ItemDataRole.UserRole: return p
        if role == Qt.ItemDataRole.CheckStateRole and c == 0:
            return Qt.CheckState.Checked if p.name in self.checked else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DecorationRole and c == 1: return self.icons.get(p.name, QIcon())
        if role == Qt.ItemDataRole.DisplayRole:
            return ("",p.title,"System" if p.system else 'User',p.status,p.version or "—",p.apk_size)[c]
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{p.title}\n{p.name}\n{p.status}" + ('\nEssential app in use' if p.protected else "")
        if role == Qt.ItemDataRole.ForegroundRole and c == 3:
            dark = bool(QApplication.instance().property("darkTheme"))
            return QColor(("#c5a3ef" if not p.installed else "#f3be72" if p.disabled else "#6cd6b4") if dark else ("#76509a" if not p.installed else "#98601c" if p.disabled else "#20775f"))

    def flags(self, index):
        f = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return f | Qt.ItemFlag.ItemIsUserCheckable if index.column() == 0 else f

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            name = self.rows[index.row()].name
            if value == Qt.CheckState.Checked.value: self.checked.add(name)
            else: self.checked.discard(name)
            self.dataChanged.emit(index,index,[role])
            self.marked.emit()
            return True
        return False

    def mark(self, names, checked=True):
        if checked: self.checked.update(names)
        else: self.checked.difference_update(names)
        if self.rows: self.dataChanged.emit(self.index(0,0),self.index(len(self.rows)-1,0),[Qt.ItemDataRole.CheckStateRole])
        self.marked.emit()


class PackageFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.mode, self.query = "enabled", ""
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    @staticmethod
    def matches(p, mode):
        if mode == "all": return True
        if mode == "removed": return not p.installed
        if not p.installed: return False
        if mode == "disabled": return p.disabled
        if p.disabled: return False
        if mode == "system": return p.system
        if mode == "user": return not p.system
        return True

    def filterAcceptsRow(self, row, parent):
        p = self.sourceModel().rows[row]
        return self.matches(p,self.mode) and (not self.query or self.query in f"{p.title} {p.name}".casefold())

    def change(self, mode=None, query=None):
        if mode is not None: self.mode = mode
        if query is not None: self.query = query.strip().casefold()
        self.invalidateFilter()


class AppDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        p = index.data(Qt.ItemDataRole.UserRole)
        if not p:
            return super().paint(painter,option,index)
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt,index)
        opt.text, opt.icon = "", QIcon()
        QApplication.style().drawControl(QStyle.ControlElement.CE_ItemViewItem,opt,painter)
        rect = option.rect
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon and not icon.isNull():
            icon.paint(painter,rect.x()+10,rect.y()+9,32,32)
        else:
            painter.save()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#dce8f5"))
            painter.drawRoundedRect(rect.x()+10,rect.y()+9,32,32,7,7)
            painter.setPen(QColor("#4778af"))
            painter.drawText(rect.x()+10,rect.y()+9,32,32,Qt.AlignmentFlag.AlignCenter,p.title[:1].upper())
            painter.restore()
        painter.save()
        x, width = rect.x()+53, rect.width()-62
        font = option.font
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(option.palette.color(QPalette.ColorRole.Text))
        painter.drawText(x,rect.y()+7,width,20,Qt.AlignmentFlag.AlignVCenter,painter.fontMetrics().elidedText(p.title,Qt.TextElideMode.ElideRight,width))
        font.setBold(False)
        font.setPointSize(max(8,font.pointSize()-1))
        painter.setFont(font)
        painter.setPen(option.palette.color(QPalette.ColorRole.PlaceholderText))
        painter.drawText(x,rect.y()+28,width,17,Qt.AlignmentFlag.AlignVCenter,painter.fontMetrics().elidedText(p.name,Qt.TextElideMode.ElideMiddle,width))
        painter.restore()


class UninstallDialog(QDialog):
    """Review target, package list and backup in one explicit confirmation."""
    def __init__(self, owner, packages, serial, user, keep=False):
        super().__init__(owner)
        self.setWindowTitle('Uninstall Apps')
        self.resize(760,580)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.addWidget(label(f"Uninstall {len(packages)} app(s)?", "heading"))
        layout.addWidget(label(f"{owner.device_title.text()} · {serial} · User {user}", "muted", True))
        self.packages = QTableWidget(len(packages),2)
        self.packages.setHorizontalHeaderLabels(['App / package', "Tipo"])
        self.packages.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.packages.setColumnWidth(1,100)
        self.packages.verticalHeader().hide()
        self.packages.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row,p in enumerate(packages):
            self.packages.setItem(row,0,QTableWidgetItem(p.title+"\n"+p.name))
            self.packages.setItem(row,1,QTableWidgetItem("System" if p.system else 'User'))
        self.packages.resizeRowsToContents()
        layout.addWidget(self.packages,1)
        self.keep_data = QCheckBox('Keep app data on the device')
        self.keep_data.setChecked(keep)
        layout.addWidget(self.keep_data)
        self.backup = QCheckBox('Save APKs and splits before uninstalling')
        self.backup.setChecked(True)
        layout.addWidget(self.backup)
        folder_row = QHBoxLayout()
        self.folder = QLineEdit(str(Path.home()/"Documents"/"DroidDesk"/"Backups"/datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))
        self.folder.setToolTip('The copy allows you to reinstall the APKs; it does not contain the app data.')
        self.browse = button('Select a folder…', self.choose_folder)
        folder_row.addWidget(self.folder,1)
        folder_row.addWidget(self.browse)
        layout.addLayout(folder_row)
        self.backup.toggled.connect(self.folder.setEnabled)
        self.backup.toggled.connect(self.browse.setEnabled)
        layout.addWidget(label('The removal applies only to this Android user. The copy contains the APKs, without any personal data. If the copy fails, that app will not be removed.',"muted",True))
        self.error = label("", "muted", True)
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = button('Cancel', self.reject)
        cancel.setDefault(True)
        self.confirm = button('Uninstall', self.confirm_removal)
        self.confirm.setObjectName("danger")
        buttons.addWidget(cancel)
        buttons.addWidget(self.confirm)
        layout.addLayout(buttons)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self,'Folder for APK copies',self.folder.text())
        if folder:
            self.folder.setText(folder)

    def backup_folder(self):
        return str(Path(self.folder.text().strip()).expanduser()) if self.backup.isChecked() else None

    def confirm_removal(self):
        if self.backup.isChecked() and not self.folder.text().strip():
            self.error.setText('Select a folder for the copy, or deselect the option to save APKs.')
            self.folder.setFocus()
            return
        self.accept()


class ResultsDialog(QDialog):
    def __init__(self, owner, outcomes, title):
        super().__init__(owner)
        self.setWindowTitle(title)
        self.resize(900,440)
        self.outcomes = outcomes
        layout = QVBoxLayout(self)
        counts = Counter(x.status for x in outcomes)
        layout.addWidget(label(f"{counts['ok']} completed    ·    {counts['error']} failed    ·    {counts['manual']} require action on Android    ·    {counts['skipped']+counts['blocked']} skipped", "heading", True))
        table = QTableWidget(len(outcomes),3)
        table.setHorizontalHeaderLabels(['Result','Package','Details'])
        names = {"ok":'Completed',"error":'Failed',"manual":"No Android","skipped":'Ignored',"blocked":'Protected'}
        for row,o in enumerate(outcomes):
            for col,text in enumerate((names.get(o.status,o.status),o.package,o.message)):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row,col,item)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0,105)
        table.setColumnWidth(1,300)
        layout.addWidget(table)
        actions = QHBoxLayout()
        def details():
            row = table.currentRow()
            if row >= 0: owner.open_details(outcomes[row].package)
        actions.addWidget(button('Open a package on Android',details))
        def save():
            target,_ = QFileDialog.getSaveFileName(self,'Save Results',"resultados.csv","CSV (*.csv)")
            if target:
                with open(target,"w",encoding="utf-8-sig",newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["package","result","details"])
                    w.writerows((o.package,o.status,o.message) for o in outcomes)
        actions.addWidget(button('Save report…',save))
        actions.addStretch()
        actions.addWidget(button('Close',self.accept,True))
        layout.addLayout(actions)


class MainWindow(QMainWindow):
    def __init__(self, autoconnect=True):
        super().__init__()
        self.setWindowTitle(f"DroidDesk {VERSION} — Android App Manager")
        self.setWindowIcon(QIcon(str(ROOT / "assets" / "droiddesk.svg")))
        self.resize(1440,900)
        self.setMinimumSize(1120,720)
        self.setAcceptDrops(True)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.tasks = set()
        self.busy = False
        self.devices = []
        self.snapshot_data = None
        self.logcat = None
        self.shell_process = None
        self.logpath = CACHE / "logs" / (datetime.now().strftime("%Y-%m-%d") + ".log")
        self.settings = QSettings("DroidDesk", "DroidDesk")
        self.model = PackageModel()
        self.proxy = PackageFilter()
        self.proxy.setSourceModel(self.model)
        self.build()
        self.theme_box.setCurrentIndex(0 if self.settings.value("theme", "dark") == "dark" else 1)
        self.change_theme()
        self.model.marked.connect(self.marked_changed)
        self.statusBar().showMessage('Connect your Android device via USB and enable debugging on the device.')
        if autoconnect: QTimer.singleShot(100,self.refresh_devices)

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(238)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18,25,18,18)
        layout.setSpacing(12)
        layout.addWidget(label("DroidDesk","brand"))
        layout.addWidget(label("ANDROID APP MANAGER","section"))
        layout.addSpacing(18)
        layout.addWidget(label('DEVICE',"section"))
        self.device_title = label('No device',"device",True)
        layout.addWidget(self.device_title)
        self.device_meta = label('USB or ADB network',"",True)
        layout.addWidget(self.device_meta)
        self.device_box = QComboBox()
        self.device_box.setToolTip('Select the device; all operations use this destination.')
        layout.addWidget(self.device_box)
        self.user_box = QComboBox()
        self.user_box.addItem('User 0 · Owner',0)
        layout.addWidget(self.user_box)
        layout.addWidget(button('Refresh Connection',self.refresh_devices))
        layout.addSpacing(15)
        layout.addWidget(label('APPS',"section"))
        self.filters = QListWidget()
        self.filters.setObjectName("filters")
        for key,name in FILTERS:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole,key)
            self.filters.addItem(item)
        self.filters.setCurrentRow(0)
        layout.addWidget(self.filters,1)
        layout.addWidget(button('Connect via Wi-Fi…',self.wireless))
        self.theme_box = QComboBox()
        self.theme_box.addItem('Dark theme', "dark")
        self.theme_box.addItem('Light theme', "light")
        self.theme_box.currentIndexChanged.connect(self.change_theme)
        layout.addWidget(self.theme_box)
        layout.addWidget(label(f"Version {VERSION} · Linux","section"))
        layout.addWidget(label(f"Creator: {CREATOR}\nCo-author: {COAUTHOR}", "", True))
        outer.addWidget(side)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24,10,24,10)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.app_page(),'Apps')
        self.tabs.addTab(self.install_page(),'Installation')
        self.tabs.addTab(self.console_page(),"Console")
        self.tabs.addTab(self.tools_page(),'Tools')
        body_layout.addWidget(self.tabs,1)
        self.progress_text = label('Ready',"muted")
        body_layout.addWidget(self.progress_text)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.hide()
        body_layout.addWidget(self.progress)
        outer.addWidget(body,1)
        self.filters.currentRowChanged.connect(self.filter_changed)
        self.device_box.currentIndexChanged.connect(self.device_changed)
        self.user_box.currentIndexChanged.connect(self.user_changed)
        QShortcut(QKeySequence("Ctrl+F"),self,activated=lambda:self.search.setFocus())
        QShortcut(QKeySequence("F5"),self,activated=self.refresh_packages)

    def app_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,20,0,0)
        top = QHBoxLayout()
        self.heading = label('Active apps',"heading")
        self.count = label('No apps loaded',"muted")
        headings = QVBoxLayout()
        headings.addWidget(self.heading)
        headings.addWidget(self.count)
        top.addLayout(headings,1)
        self.refresh_button = button('Update list',self.refresh_packages)
        self.names_button = button('Update Names and Icons',lambda:self.refresh_packages(names=True))
        top.addWidget(self.names_button)
        top.addWidget(self.refresh_button)
        layout.addLayout(top)
        layout.addSpacing(9)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search by app or package name…  Ctrl+F')
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.search_changed)
        layout.addWidget(self.search)
        mini = QHBoxLayout()
        mini.addWidget(button('Mark as visible',self.mark_visible,quiet=True))
        mini.addWidget(button('Clear Selections',lambda:self.model.mark(set(self.model.checked),False),quiet=True))
        mini.addStretch()
        mini.addWidget(button('Load preset…',self.load_preset,quiet=True))
        mini.addWidget(button('Save preset…',self.save_preset,quiet=True))
        layout.addLayout(mini)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setItemDelegateForColumn(1,AppDelegate(self.table))
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(1,Qt.SortOrder.AscendingOrder)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(52)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0,34)
        self.table.setColumnWidth(2,82)
        self.table.setColumnWidth(3,175)
        self.table.setColumnWidth(4,95)
        self.table.setColumnWidth(5,80)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.table.selectionModel().currentRowChanged.connect(self.inspect_row)
        self.table.doubleClicked.connect(lambda i:self.toggle_mark(i))
        self.table.installEventFilter(self)
        split.addWidget(self.table)
        self.inspector = QFrame()
        self.inspector.setObjectName("inspector")
        self.inspector.setMinimumWidth(245)
        self.inspector.setMaximumWidth(300)
        info = QVBoxLayout(self.inspector)
        info.setContentsMargins(17,22,17,15)
        self.app_icon = QLabel()
        self.app_icon.setFixedSize(58,58)
        self.app_name = label('Select an app',"",True)
        self.app_name.setFont(QFont("Noto Sans",13,QFont.Weight.DemiBold))
        self.app_package = label('The details are provided here.',"muted",True)
        self.app_package.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.addWidget(self.app_icon)
        info.addWidget(self.app_name)
        info.addWidget(self.app_package)
        info.addSpacing(12)
        self.app_details = label("","detailContent",True)
        self.app_details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_scroll = QScrollArea()
        details_scroll.setWidgetResizable(True)
        details_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.app_details.setAlignment(Qt.AlignmentFlag.AlignTop)
        details_scroll.setWidget(self.app_details)
        info.addWidget(details_scroll,1)
        self.open_button = button('Open app',lambda:self.single_tool("launch"))
        self.details_button = button('Details on Android',lambda:self.single_tool("details"))
        self.permissions_button = button('Permissions…',self.show_permissions)
        self.stop_button = button('Force Shutdown',lambda:self.single_action("stop"))
        for b in (self.open_button,self.details_button,self.permissions_button,self.stop_button):
            info.addWidget(b)
            b.setEnabled(False)
        split.addWidget(self.inspector)
        split.setStretchFactor(0,1)
        layout.addWidget(split,1)
        actionbar = QFrame()
        actionbar.setObjectName("card")
        actions = QHBoxLayout(actionbar)
        actions.setContentsMargins(12,12,12,12)
        self.marked_label = label('0 selected',"muted")
        actions.addWidget(self.marked_label)
        actions.addStretch()
        self.keep_data = QCheckBox('Retain data')
        self.keep_data.setToolTip('Preserve data when uninstalling for this user.')
        self.keep_data.hide()
        actions.addWidget(self.keep_data)
        self.operation = QComboBox()
        for name,key in OPERATIONS: self.operation.addItem(name,key)
        self.operation.setToolTip('Select an action for the selected apps. Refreshing and filtering do not change this selection.')
        actions.addWidget(self.operation)
        self.execute_button = button('Run',self.execute,True)
        self.execute_button.setEnabled(False)
        actions.addWidget(self.execute_button)
        self.uninstall_button = button('Uninstall…',self.uninstall_marked)
        self.uninstall_button.setObjectName("danger")
        self.uninstall_button.setEnabled(False)
        actions.addWidget(self.uninstall_button)
        self.operation.currentIndexChanged.connect(self.marked_changed)
        layout.addWidget(actionbar)
        return page

    def install_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,22,0,0)
        layout.addWidget(label('Install apps',"heading"))
        layout.addWidget(label('Add APKs to the queue. For a split app, select the "splits" option.',"muted",True))
        controls = QHBoxLayout()
        controls.addWidget(button('Add APKs…',self.add_apks))
        controls.addWidget(button('Add folder…',self.add_apk_folder))
        controls.addWidget(button('Remove from the queue',lambda:[self.install_list.takeItem(self.install_list.row(x)) for x in self.install_list.selectedItems()]))
        controls.addStretch()
        layout.addLayout(controls)
        self.install_list = QListWidget()
        self.install_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.install_list,1)
        self.split_install = QCheckBox('All the APKs in the queue are versions of the same app')
        layout.addWidget(self.split_install)
        layout.addWidget(button('Install queue',self.install_queue,True),alignment=Qt.AlignmentFlag.AlignRight)
        return page

    def console_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,18,0,0)
        head = QHBoxLayout()
        head.addWidget(label("Console ADB","heading"))
        head.addStretch()
        head.addWidget(button('Save log…',self.save_log))
        head.addWidget(button('Clear',lambda:self.console.clear()))
        layout.addLayout(head)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(12000)
        layout.addWidget(self.console,1)
        quick = QHBoxLayout()
        for text,cmd in [('Battery',"shell dumpsys battery"),('Storage',"shell df -h /data"),("Screen","shell wm size"),('Users',"shell pm list users")]:
            quick.addWidget(button(text,lambda _,c=cmd:self.command.setText(c)))
        quick.addStretch()
        self.logcat_button = button('Start logcat',self.toggle_logcat)
        quick.addWidget(self.logcat_button)
        layout.addLayout(quick)
        bottom = QHBoxLayout()
        self.console_mode = QComboBox()
        self.console_mode.addItems(["ADB","Fastboot"])
        bottom.addWidget(self.console_mode)
        self.command = QLineEdit()
        self.command.setPlaceholderText('ADB command, for example: shell pm list packages -3')
        self.command.returnPressed.connect(self.run_console)
        bottom.addWidget(self.command,1)
        bottom.addWidget(button('Run',self.run_console,True))
        layout.addLayout(bottom)
        return page

    def tools_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0,22,0,0)
        layout.addWidget(label('Device Tools',"heading"))
        layout.addWidget(label('Operations on the device and user selected on the side.',"muted"))
        grid = QGridLayout()
        specs = [
            ('Screen and files',[('Take screenshot…',self.screenshot),('Control the screen with scrcpy',self.scrcpy),('Upload files to Downloads…',self.push_files)]),
            ('Android Screen',[('View resolution',lambda:self.tool_command("shell","wm","size")),('Change resolution…',self.resolution),('Change density…',self.density),('Status bar icons…',self.status_icons),('Restore resolution',lambda:self.confirm_tool('Restore resolution?',["shell","wm","size","reset"])),('Restore density',lambda:self.confirm_tool('Restore density?',["shell","wm","density","reset"]))]),
            ('Restart',[('Restart Android',lambda:self.reboot("")),('Restart in recovery mode',lambda:self.reboot("recovery")),('Reboot into bootloader',lambda:self.reboot("bootloader"))]),
            ('Diagnosis',[('Battery Information',lambda:self.tool_command("shell","dumpsys","battery")),('Storage space',lambda:self.tool_command("shell","df","-h","/data")),('Open Settings on Android',lambda:self.tool_command("shell","am","start","-a","android.settings.SETTINGS"))]),
        ]
        for i,(title,items) in enumerate(specs):
            box = QGroupBox(title)
            col = QVBoxLayout(box)
            col.setContentsMargins(16,20,16,16)
            for text,fn in items: col.addWidget(button(text,fn))
            col.addStretch()
            grid.addWidget(box,i//2,i%2)
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def log(self,text):
        self.console.appendPlainText(text)
        try:
            self.logpath.parent.mkdir(parents=True,exist_ok=True)
            with self.logpath.open("a",encoding="utf-8") as f: f.write(text+"\n")
        except OSError: pass

    def submit(self, fn, callback=None, text='Running…'):
        if self.busy:
            self.statusBar().showMessage('Please wait while the operation is in progress.',5000)
            return
        self.busy = True
        for widget in (self.device_box,self.user_box,self.refresh_button,self.names_button,self.execute_button,self.uninstall_button,self.operation): widget.setEnabled(False)
        self.progress.show()
        self.progress.setRange(0,0)
        self.progress_text.setText(text)
        task = Task(fn)
        self.tasks.add(task)
        def finish():
            self.busy = False
            self.progress.hide()
            for widget in (self.device_box,self.user_box,self.refresh_button,self.names_button,self.operation): widget.setEnabled(True)
            self.marked_changed()
            self.tasks.discard(task)
        def done(value):
            finish()
            self.progress_text.setText('Ready')
            if callback: callback(value)
        def failed(message):
            finish()
            self.progress_text.setText('The operation failed; check the console.')
            QMessageBox.warning(self,'It was not possible to complete',message[:2500])
        task.signals.done.connect(done)
        task.signals.error.connect(failed)
        task.signals.log.connect(self.log)
        task.signals.progress.connect(self.on_progress)
        self.pool.start(task)

    def on_progress(self,current,total,text):
        self.progress.setRange(0,total if total else 0)
        self.progress.setValue(current)
        self.progress_text.setText(text + (f"   {current}/{total}" if total else ""))

    def target(self):
        serial = self.device_box.currentData()
        if not serial:
            QMessageBox.information(self,'Connect your device',"Connect your Android device and enable USB debugging on the device's screen.")
            return None
        device = next((x for x in self.devices if x.serial == serial),None)
        if not device or device.state != "device":
            QMessageBox.information(self,'Device unavailable','Enable the debug key on Android and refresh the connection.')
            return None
        return serial,int(self.user_box.currentData() or 0)

    def refresh_devices(self):
        self.submit(lambda p,l:Adb(l).devices(),self.devices_loaded,'Searching for devices…')

    def devices_loaded(self,devices):
        old = self.device_box.currentData()
        self.devices = devices
        self.device_box.blockSignals(True)
        self.device_box.clear()
        for d in devices:
            state = {"device":"USB / ADB","unauthorized":'Authorize on Android',"offline":"Offline"}.get(d.state,d.state)
            self.device_box.addItem(f"{d.model} · {state}",d.serial)
        if old:
            i = self.device_box.findData(old)
            if i >= 0: self.device_box.setCurrentIndex(i)
        self.device_box.blockSignals(False)
        if devices: self.device_changed()
        else:
            self.device_title.setText('No device')
            self.device_meta.setText('Connect via USB and enable debugging on Android.')
            self.snapshot_data = None
            self.model.set_packages([])

    def device_changed(self,*_):
        if self.logcat: self.toggle_logcat()
        if self.shell_process: self.shell_process.terminate()
        self.model.checked.clear()
        self.snapshot_data = None
        self.model.set_packages([])
        self.user_box.blockSignals(True)
        self.user_box.clear()
        self.user_box.addItem('User 0 · Owner',0)
        self.user_box.blockSignals(False)
        if self.device_box.currentData():
            self.device_title.setText(self.device_box.currentText().split(" · ")[0])
            self.refresh_packages()

    def user_changed(self,*_):
        if not self.snapshot_data: return
        self.model.checked.clear()
        self.snapshot_data = None
        self.model.set_packages([])
        self.refresh_packages()

    def refresh_packages(self,*_,names=False):
        if self.busy: return
        target = self.target()
        if not target: return
        serial,user = target
        self.submit(lambda p,l:Adb(l).snapshot(serial,user,p,names),self.loaded,'Loading apps…')

    def loaded(self,snapshot):
        self.snapshot_data = snapshot
        self.model.set_packages(snapshot.packages)
        info = snapshot.info
        self.device_title.setText(info["model"])
        self.device_meta.setText(f"{info['brand'].title()} · Android {info['android']}\nAPI {info['api']} · {info['serial']}")
        user = self.user_box.currentData() or 0
        self.user_box.blockSignals(True)
        self.user_box.clear()
        for uid,name in snapshot.users: self.user_box.addItem(f"User {uid} · {name}",uid)
        index = self.user_box.findData(user)
        if index >= 0: self.user_box.setCurrentIndex(index)
        self.user_box.blockSignals(False)
        self.update_counts()
        self.filter_changed(self.filters.currentRow())
        self.statusBar().showMessage(f"{len(snapshot.packages)} apps loaded. All actions use user {user}.")

    def update_counts(self):
        for i,(key,name) in enumerate(FILTERS):
            count = sum(self.proxy.matches(p,key) for p in self.model.rows)
            self.filters.item(i).setText(f"{name}    {count}")
        self.count.setText(f"{self.proxy.rowCount()} app(s) nesta lista")

    def filter_changed(self,index):
        if index < 0: return
        key,name = FILTERS[index]
        self.proxy.change(mode=key)
        self.heading.setText('Apps ' + name.casefold() if key in {"enabled","disabled","removed"} else 'Apps · ' + name)
        self.count.setText(f"{self.proxy.rowCount()} app(s) nesta lista")
        self.marked_changed()
        self.tabs.setCurrentIndex(0)

    def search_changed(self,query):
        self.proxy.change(query=query)
        self.count.setText(f"{self.proxy.rowCount()} app(s) nesta lista")

        self.marked_changed()

    def mark_visible(self):
        self.model.mark({self.proxy.index(i,0).data(Qt.ItemDataRole.UserRole).name for i in range(self.proxy.rowCount())})

    def marked_changed(self):
        count = len(self.model.checked)
        visible = {self.proxy.index(i,0).data(Qt.ItemDataRole.UserRole).name for i in range(self.proxy.rowCount())}
        hidden = len(self.model.checked - visible)
        self.marked_label.setText(f"{count} marcado(s)" + (f" · {hidden} fora do filtro" if hidden else ""))
        self.execute_button.setText(self.operation.currentText() + (f" ({count})" if count else ""))
        self.execute_button.setEnabled(bool(count) and not self.busy)
        self.uninstall_button.setEnabled(bool(count) and not self.busy)

    def change_theme(self, *_):
        theme = self.theme_box.currentData() or "dark"
        apply_theme(QApplication.instance(), theme)
        self.settings.setValue("theme", theme)
        self.table.viewport().update()

    def uninstall_marked(self):
        packages = [p for p in self.model.rows if p.name in self.model.checked]
        if packages:
            self.execute_packages(packages,"uninstall")


    def toggle_mark(self,index):
        if index.isValid():
            p=index.data(Qt.ItemDataRole.UserRole)
            self.model.mark({p.name},p.name not in self.model.checked)

    def eventFilter(self,obj,event):
        if obj is self.table and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Space:
            for index in self.table.selectionModel().selectedRows(): self.toggle_mark(index)
            return True
        return super().eventFilter(obj,event)

    def current_package(self):
        index = self.table.currentIndex()
        return index.data(Qt.ItemDataRole.UserRole) if index.isValid() else None

    def inspect_row(self,current,*_):
        p=current.data(Qt.ItemDataRole.UserRole)
        for b in (self.open_button,self.details_button,self.permissions_button,self.stop_button): b.setEnabled(bool(p))
        if not p:
            self.app_name.setText('Select an app')
            self.app_package.setText('The details are provided here.')
            self.app_details.clear()
            self.app_icon.clear()
            return
        self.app_name.setText(p.title)
        self.app_package.setText(p.name)
        icon = self.model.icons.get(p.name,QIcon())
        self.app_icon.setPixmap(icon.pixmap(56,56))
        self.app_details.setText(f"<b>{p.status}</b><br><br>{'System' if p.system else 'User'}<br>Version: {p.version or '—'}<br>APKs: {p.apk_size}<br>UID: {p.uid or '—'}<br>Android target: {p.target_sdk or '—'}<br><br>" + (f"Last disabled by:<br>{p.caller}<br><br>" if p.caller else "") + ('Android requires reactivation through the system screen. Use "Details" on Android.' if p.disabled and p.state in {2,4} else ""))
        self.open_button.setEnabled(p.installed and not p.disabled)
        self.permissions_button.setEnabled(p.installed)
        self.stop_button.setEnabled(p.installed)

    def context_menu(self,pos):
        index=self.table.indexAt(pos)
        if not index.isValid(): return
        self.table.setCurrentIndex(index)
        p=index.data(Qt.ItemDataRole.UserRole)
        menu=QMenu(self)
        for name,operation in [('Reactivate' if p.disabled else 'Disable',"enable" if p.disabled else "disable"),('Restore',"restore"),('Export APKs…',"export"),('Uninstall for this user…',"uninstall")]:
            if operation=="restore" and p.installed: continue
            if operation!="restore" and not p.installed: continue
            menu.addAction(name,lambda _,o=operation:self.execute_packages([p],o))
        menu.addSeparator()
        menu.addAction('Details on Android',lambda:self.open_details(p.name))
        menu.addAction('Permissions…',self.show_permissions)
        menu.addAction('Force Shutdown',lambda:self.single_action("stop"))
        menu.addAction('Clear data…',lambda:self.single_action("clear"))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def execute(self):
        packages = [p for p in self.model.rows if p.name in self.model.checked]
        if packages: self.execute_packages(packages,self.operation.currentData())

    def execute_packages(self,packages,operation):
        if self.busy: return
        target=self.target()
        if not target: return
        serial,user=target
        if operation=="export":
            folder=QFileDialog.getExistingDirectory(self,'Save APKs and splits')
            if folder: self.submit(lambda p,l:Adb(l).export(serial,user,packages,folder,p),lambda x:self.results(x,'Export'))
            return
        title=dict((key,name) for name,key in OPERATIONS).get(operation,{"clear":'Clear Data',"stop":'Force Shutdown'}.get(operation,operation))
        text=f"{title}: {len(packages)} app(s)\nDevice: {self.device_title.text()} · User {user}\n\n" + "\n".join(p.title for p in packages[:10])
        if len(packages)>10: text+=f"\n… e mais {len(packages)-10}"
        if operation=="clear": text+='\n\nThe data and settings for this app will be deleted.'
        self.log(f"[Request] {title} · device {serial} · user {user} · " + ", ".join(p.name for p in packages))
        folder = None
        keep = self.keep_data.isChecked()
        if operation == "uninstall":
            review = UninstallDialog(self, packages, serial, user, keep)
            if review.exec() != QDialog.DialogCode.Accepted:
                self.log('[Canceled] Uninstallation canceled before sending commands to Android.')
                self.progress_text.setText('Uninstallation canceled. No applications were removed.')
                return
            folder = review.backup_folder()
            keep = review.keep_data.isChecked()
            self.keep_data.setChecked(keep)
        else:
            review=QMessageBox(QMessageBox.Icon.Question,title,text,QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,self)
            review.setDefaultButton(QMessageBox.StandardButton.Cancel)
            if review.exec()!=QMessageBox.StandardButton.Yes:
                self.log(f"[Canceled] {title} canceled before sending commands to Android.")
                self.progress_text.setText(f"{title}: cancelado.")
                return
        def work(progress,log):
            a=Adb(log)
            if not folder:return a.batch(serial,user,packages,operation,progress,keep)
            exports={x.package:x for x in a.export(serial,user,packages,folder,progress)}
            outcomes=[]
            for i,p in enumerate(packages):
                progress(i,len(packages),'Uninstalling '+p.title)
                saved=exports[p.name]
                outcomes.append(a.action(serial,user,p,operation,keep) if saved.status=="ok" else Outcome(p.name,"error",'Backup failed; package preserved. '+saved.message))
            return outcomes
        self.submit(work,lambda x:self.results(x,title,refresh=True))

    def results(self,outcomes,title,refresh=False):
        for outcome in outcomes:
            self.log(f"[Resultado] {title} · {outcome.package} · {outcome.status}: {outcome.message}")
        ResultsDialog(self,outcomes,title).exec()
        if refresh:
            self.model.checked.clear()
            self.refresh_packages()

    def open_details(self,name):
        target=self.target()
        if target: self.submit(lambda p,l:Adb(l).details(*target,name),lambda _:self.statusBar().showMessage('The app screen is open on Android. Tap "Enable," if available.',10000))

    def single_tool(self,operation):
        p=self.current_package()
        if not p: return
        if operation=="details": self.open_details(p.name)
        else:
            target=self.target()
            if target: self.submit(lambda pr,l:Adb(l).launch(*target,p.name))

    def single_action(self,operation):
        p=self.current_package()
        if p:self.execute_packages([p],operation)

    def save_preset(self):
        if not self.model.checked:
            QMessageBox.information(self,"Preset",'Select the apps you want to save to the preset.')
            return
        path,_=QFileDialog.getSaveFileName(self,'Save preset',"preset-droiddesk.txt",'Text (*.txt)')
        if path:
            text="# DroidDesk preset\n# "+self.device_title.text()+"\n"+"\n".join(sorted(self.model.checked))+"\n"
            Path(path).write_text(text,encoding="utf-8")
            self.statusBar().showMessage(f"Preset saved with {len(self.model.checked)} packages.",8000)

    def load_preset(self):
        path,_=QFileDialog.getOpenFileName(self,'Load preset',"",'Text (*.txt);;All (*)')
        if not path:return
        try: names=read_preset(path)
        except (OSError,UnicodeError) as exc:
            QMessageBox.warning(self,"Preset",str(exc));return
        available={p.name for p in self.model.rows}
        self.model.mark(names&available)
        self.statusBar().showMessage(f"Preset: {len(names&available)} of {len(names)} packages found and selected.",10000)

    def add_apks(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Add APKs',"","Android (*.apk)")
        self.add_install_files(paths)

    def add_apk_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Folder with APKs')
        if folder:self.add_install_files([str(p) for p in sorted(Path(folder).glob("*.apk"))])

    def add_install_files(self,paths):
        current={self.install_list.item(i).text() for i in range(self.install_list.count())}
        for path in paths:
            if path not in current:self.install_list.addItem(path)

    def install_queue(self):
        files=[self.install_list.item(i).text() for i in range(self.install_list.count())]
        target=self.target()
        if not target or not files:return
        split=self.split_install.isChecked()
        self.submit(lambda p,l:Adb(l).install(*target,files,split,p),lambda x:self.results(x,'Installation',True))

    def show_permissions(self):
        package=self.current_package()
        target=self.target()
        if not package or not target:return
        self.submit(lambda p,l:Adb(l).permissions(*target,package.name),lambda rows:self.permissions_dialog(package,rows,target))

    def permissions_dialog(self,package,rows,target):
        dialog=QDialog(self)
        dialog.setWindowTitle('Permissions · '+package.title)
        dialog.resize(850,480)
        layout=QVBoxLayout(dialog)
        layout.addWidget(label('Permissions Declared by the App',"heading"))
        layout.addWidget(label('Android may deny permissions that are system-defined or that the app has not declared.',"muted",True))
        table=QTableWidget(len(rows),3)
        table.setHorizontalHeaderLabels(['Permission','Granted',"Flags"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for i,(name,granted,flags) in enumerate(rows):
            for c,text in enumerate((name,"Sim" if granted else 'No',flags)):
                item=QTableWidgetItem(text);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);table.setItem(i,c,item)
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table,1)
        bar=QHBoxLayout()
        def change(grant):
            row=table.currentRow()
            if row<0:return
            perm=rows[row][0]
            def done(_):
                table.item(row,1).setText("Sim" if grant else 'No')
                self.statusBar().showMessage('Permission updated.',5000)
            self.submit(lambda p,l:Adb(l).set_permission(*target,package.name,perm,grant),done)
        bar.addWidget(button('Grant',lambda:change(True)))
        bar.addWidget(button('Revoke',lambda:change(False)))
        bar.addStretch()
        bar.addWidget(button('Close',dialog.accept))
        layout.addLayout(bar)
        dialog.exec()

    def run_console(self):
        text=self.command.text().strip()
        if not text:return
        try: args=shlex.split(text)
        except ValueError as exc:QMessageBox.warning(self,'Command',str(exc));return
        if self.console_mode.currentText()=="Fastboot" or (args and args[0]=="fastboot"):
            self.run_fastboot(args[1:] if args and args[0]=="fastboot" else args)
            return
        target=self.target()
        if not target:return
        if self.shell_process:
            self.shell_process.write((text+"\n").encode())
            self.command.clear()
            return
        if args and args[0]=="adb":args.pop(0)
        if not args:return
        if args[0] in {"-s","-t","-d","-e"}:
            QMessageBox.warning(self,'Command Destination','Select the device on the side. Remove destination options from the command.');return
        if args==["shell"]:
            self.start_shell(target[0])
            return
        if args[0]=="logcat":
            if not self.logcat:self.start_logcat(args)
            return
        self.submit(lambda p,l:Adb(l).run(*args,serial=target[0],timeout=180,quiet=True),self.log)

    def run_fastboot(self,args):
        executable=shutil.which("fastboot")
        if not executable:
            QMessageBox.information(self,"Fastboot",'Install the Linux fastboot package to use this mode.')
            return
        if not args:return
        if args[0] in {"-s","-t"}:
            QMessageBox.information(self,"Fastboot",'Select the device using the program, without using -s or -t.');return
        destructive=any(x in {"flash","erase","format","flashing","oem","-w","update"} for x in args)
        if destructive and QMessageBox.warning(self,'Confirm Fastboot Command',shlex.join(args)+'\n\nThis command can modify partitions or erase data.',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Yes:return
        preferred=self.device_box.currentData()
        def work(progress,log):
            discovery=subprocess.run([executable,"devices"],capture_output=True,text=True,timeout=10)
            serials=[line.split()[0] for line in discovery.stdout.splitlines() if line.split()]
            if args[0]=="devices":return discovery.stdout+discovery.stderr
            if not serials:raise AdbError('No device is in Fastboot. Samsung tablets typically use Download Mode.')
            selected=preferred
            if selected not in serials:
                if len(serials)>1:raise AdbError('There is more than one device in Fastboot. Connect only the device that is the target of this operation.')
                selected=serials[0]
            cmd=[executable,"-s",selected,*args]
            log("$ "+shlex.join(cmd))
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=180)
            output=result.stdout+result.stderr
            if result.returncode:raise AdbError(output)
            return output
        self.submit(work,self.log)

    def start_shell(self,serial):
        process=QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda:self.log(bytes(process.readAllStandardOutput()).decode("utf-8","replace")))
        def finished(*_):
            self.shell_process=None
            self.command.setPlaceholderText('ADB command, for example: shell pm list packages -3')
            self.log('Shell closed.')
        process.finished.connect(finished)
        self.shell_process=process
        process.start(shutil.which("adb"),["-s",serial,"shell"])
        self.command.clear()
        self.command.setPlaceholderText('Android Interactive Shell · Type "exit" to exit')
        self.log('Interactive shell started on '+serial)

    def save_log(self):
        path,_=QFileDialog.getSaveFileName(self,'Save log',"droiddesk.log","Log (*.log)")
        if path:Path(path).write_text(self.console.toPlainText(),encoding="utf-8")

    def toggle_logcat(self):
        if self.logcat:
            self.logcat.terminate()
            self.logcat=None
            self.logcat_button.setText('Start logcat')
            return
        self.start_logcat(["logcat","-v","time","-T","1"])

    def start_logcat(self,args):
        target=self.target()
        if not target:return
        process=QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda:self.log(bytes(process.readAllStandardOutput()).decode("utf-8","replace")))
        process.start(shutil.which("adb"),["-s",target[0],*args])
        self.logcat=process
        self.logcat_button.setText('Stop logcat')

    def tool_command(self,*args):
        target=self.target()
        if target:
            self.tabs.setCurrentIndex(2)
            self.submit(lambda p,l:Adb(l).run(*args,serial=target[0]))

    def confirm_tool(self,title,args):
        if QMessageBox.question(self,title,'Apply to the selected device?')==QMessageBox.StandardButton.Yes:self.tool_command(*args)

    def screenshot(self):
        target=self.target()
        if not target:return
        path,_=QFileDialog.getSaveFileName(self,'Save Screenshot',f"Android-{datetime.now():%Y%m%d-%H%M%S}.png","PNG (*.png)")
        if not path:return
        def work(p,l):
            data=Adb(l).run("exec-out","screencap","-p",serial=target[0],binary=True)
            if not data.startswith(b"\x89PNG"):raise AdbError('Android did not return a valid PNG image.')
            Path(path).write_bytes(data)
            return path
        self.submit(work,lambda _:self.statusBar().showMessage('Screenshot saved to '+path,10000))

    def scrcpy(self):
        target=self.target()
        if not target:return
        executable=shutil.which("scrcpy")
        if not executable:
            QMessageBox.information(self,'Screen Control','Install scrcpy on Linux to use screen control. The other features remain available.')
            return
        QProcess.startDetached(executable,["-s",target[0]])

    def push_files(self):
        target=self.target()
        if not target:return
        paths,_=QFileDialog.getOpenFileNames(self,'Send Files to Android')
        if not paths:return
        def work(progress,log):
            a=Adb(log);result=[]
            for i,path in enumerate(paths):
                progress(i,len(paths),'Sending '+Path(path).name)
                try:a.run("push",path,"/sdcard/Download/",serial=target[0],timeout=240);result.append(Outcome(Path(path).name,"ok",'Moved to Downloads.'))
                except AdbError as exc:result.append(Outcome(Path(path).name,"error",str(exc)))
            return result
        self.submit(work,lambda x:self.results(x,'File Upload'))

    def resolution(self):
        size,ok=QInputDialog.getText(self,'Resolution','New resolution, for example, 1920x1200:')
        if ok:
            import re
            if re.fullmatch(r"[1-9][0-9]{2,3}x[1-9][0-9]{2,3}",size):self.confirm_tool('Change the resolution?',["shell","wm","size",size])
            else:QMessageBox.information(self,'Resolution','Use width x height in pixels, without spaces.')

    def density(self):
        value,ok=QInputDialog.getInt(self,'Screen density','Density in DPI:',320,120,800)
        if ok:self.confirm_tool('Change the density?',["shell","wm","density",str(value)])

    def status_icons(self):
        target=self.target()
        if not target:return
        self.submit(lambda p,l:Adb(l).run("shell","settings","--user",str(target[1]),"get","secure","icon_blacklist",serial=target[0]),lambda value:self.status_icons_dialog(target,value))

    def status_icons_dialog(self,target,value):
        current=set(value.split(",")) if value and value!="null" else set()
        dialog=QDialog(self);dialog.setWindowTitle('Status bar icons')
        layout=QVBoxLayout(dialog)
        layout.addWidget(label('Choose which icons to hide on Android.',"",True))
        names=[("alarm_clock",'Alarm'),("volume","Volume"),("bluetooth","Bluetooth"),("location",'Location'),("cast",'Broadcast'),("nfc","NFC"),("headset",'Headset'),("rotate",'Rotation'),("hotspot",'Wi-Fi Router')]
        checks={}
        for slot,name in names:
            box=QCheckBox(name);box.setChecked(slot in current);checks[slot]=box;layout.addWidget(box)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        hidden=current.difference(checks)|{slot for slot,box in checks.items() if box.isChecked()}
        args=["shell","settings","--user",str(target[1])]+(["put","secure","icon_blacklist",",".join(sorted(hidden))] if hidden else ["delete","secure","icon_blacklist"])
        self.submit(lambda p,l:Adb(l).run(*args,serial=target[0]),lambda _:self.statusBar().showMessage('Icon preferences have been updated. The manufacturer may omit some items.',10000))

    def reboot(self,mode):
        self.confirm_tool('Restart the device'+(" em "+mode if mode else "")+"?",["reboot"]+([mode] if mode else []))

    def wireless(self):
        host,ok=QInputDialog.getText(self,'Wireless connection','Android IP address and port (e.g., 192.168.1.10:37001):')
        if not ok or not host:return
        import re
        if not re.fullmatch(r"[A-Za-z0-9.\[\]:_-]+:\d{2,5}",host):
            QMessageBox.information(self,'Address','Report IP:port, as shown in Android wireless debugging.');return
        choice=QMessageBox.question(self,'Pairing','Is this address the code-pairing port?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No|QMessageBox.StandardButton.Cancel)
        if choice==QMessageBox.StandardButton.Cancel:return
        if choice==QMessageBox.StandardButton.Yes:
            code,ok=QInputDialog.getText(self,"Parear Android",'Code displayed on Android:',QLineEdit.EchoMode.Password)
            if not ok or not code:return
            self.submit(lambda p,l:Adb().run("pair",host,code),lambda x:QMessageBox.information(self,'Pairing',x))
        else:self.submit(lambda p,l:Adb(l).run("connect",host),lambda _:self.refresh_devices())

    def closeEvent(self,event):
        if self.busy:
            QMessageBox.information(self,'Operation in progress','Please wait for the operation to finish before closing.')
            event.ignore();return
        if self.logcat:self.logcat.terminate()
        if self.shell_process:self.shell_process.terminate()
        event.accept()

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(u.toLocalFile().lower().endswith(".apk") for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self,event):
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile() and u.toLocalFile().lower().endswith(".apk")]
        self.add_install_files(paths)
        self.tabs.setCurrentIndex(1)
        event.acceptProposedAction()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName("DroidDesk")
    app.setDesktopFileName("droiddesk")
    app.setOrganizationName("DroidDesk")
    app.setStyle("Fusion")
    apply_theme(app, "dark")
    window=MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__=="__main__":main()
