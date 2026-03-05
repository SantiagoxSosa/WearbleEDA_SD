from database import SubjectDataDialog, SubjectSelectionDialog
from hardwareDiagnostics import HardwareDiagnosticsDialog
from activity import ActivityProfileDialog
from colorConstraints import *
from rawdata import HardwareIngestionThread, SensorPacket, get_available_ports
from simdata import SimulationIngestionThread
from eda_process import EDAProcessor
from ppg import PPGProcessor
from hrv import HRVProcessor

import sys
import datetime
import random
import numpy as np
import psutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                               QGroupBox, QFrame, QStatusBar, QMenuBar, QMenu, 
                               QDialog, QListWidget, QStackedWidget, QMessageBox,
                               QGridLayout, QTabWidget, QToolButton, QFileDialog, QTextEdit, QComboBox, QFormLayout, QDoubleSpinBox,
                               QSizePolicy, QSplitter, QAbstractItemView, QStyle, QCheckBox)
from PySide6.QtCore import Qt, QTimer, QSize, QTime
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QPalette

import pyqtgraph as pg

# --- CUSTOM MODAL DIALOGS ---
class StyledDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(ResearchStyleSheet.get_stylesheet())
        self.layout_main = QVBoxLayout(self)

class ConnectDialog(StyledDialog):
    def __init__(self, parent=None):
        super().__init__("Device Connection", parent)
        self.setFixedSize(450, 400)
        
        header = QLabel("Available Serial Ports")
        header.setObjectName("h1")
        self.layout_main.addWidget(header)
        
        self.list_widget = QListWidget()
        self.layout_main.addWidget(self.list_widget)
        
        self.chk_debug = QCheckBox("Debug Mode (Simulation)")
        self.chk_debug.setStyleSheet(f"color: {COLOR_TEXT}; font-weight: bold; margin: 10px 0;")
        self.chk_debug.toggled.connect(self.on_debug_toggled)
        self.layout_main.addWidget(self.chk_debug)
        
        btn_box = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_connect)
        self.layout_main.addLayout(btn_box)
        
        self.selected_port = None
        self.debug_mode = False
        self.populate_ports()

    def on_debug_toggled(self, checked):
        self.debug_mode = checked
        self.list_widget.setEnabled(not checked)
        if checked:
            self.btn_connect.setEnabled(True)
        else:
            self.populate_ports()

    def populate_ports(self):
        ports = get_available_ports()
        self.list_widget.clear()
        if ports:
            self.list_widget.addItems(sorted(ports))
            self.list_widget.setCurrentRow(0)
            self.btn_connect.setEnabled(True)
        else:
            self.list_widget.addItem("No ports found")
            self.btn_connect.setEnabled(False)

    def accept(self):
        if self.debug_mode:
            self.selected_port = "Simulation"
            super().accept()
        elif self.list_widget.currentItem() and self.list_widget.currentItem().text() != "No ports found":
            self.selected_port = self.list_widget.currentItem().text()
            super().accept()

class ExitDialog(StyledDialog):
    def __init__(self, parent=None, title="Save Session?", header="End Session", text="Do you want to save the session before exiting?"):
        super().__init__(title, parent)
        self.setFixedSize(400, 180)
        
        lbl_header = QLabel(header)
        lbl_header.setObjectName("h1")
        self.layout_main.addWidget(lbl_header)
        
        self.layout_main.addWidget(QLabel(text))
        
        btn_box = QHBoxLayout()
        self.btn_save = QPushButton("Save")
        self.btn_discard = QPushButton("Don't Save")
        self.btn_discard.setObjectName("secondary")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondary")
        
        self.btn_save.clicked.connect(self.on_save)
        self.btn_discard.clicked.connect(self.on_discard)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_box.addWidget(self.btn_save)
        btn_box.addWidget(self.btn_discard)
        btn_box.addWidget(self.btn_cancel)
        self.layout_main.addLayout(btn_box)
        
        self.action = None 

    def on_save(self):
        self.action = 'save'
        self.accept()

    def on_discard(self):
        self.action = 'discard'
        self.accept()

class HardwareConfigDialog(StyledDialog):
    def __init__(self, current_rate, eda_win, ppg_win, hrv_win, parent=None):
        super().__init__("Hardware Configuration", parent)
        self.setFixedSize(400, 350)
        
        # Header
        header = QLabel("Acquisition Settings")
        header.setObjectName("h1")
        self.layout_main.addWidget(header)
        
        # Settings Group
        grp = QGroupBox("Global Parameters")
        form = QFormLayout()
        
        self.combo_rate = QComboBox()
        rates = [20, 50, 64, 100, 128, 250, 256, 500, 1000]
        for r in rates:
            self.combo_rate.addItem(f"{r} Hz", r)
            
        idx = self.combo_rate.findData(current_rate)
        if idx >= 0:
            self.combo_rate.setCurrentIndex(idx)
            
        # Window Settings
        self.combo_eda = QComboBox()
        self.combo_eda.setToolTip("Time window for Phasic/Tonic decomposition")
        for w in [10, 30, 60, 120, 300]:
            self.combo_eda.addItem(f"{w} s", w)
        idx = self.combo_eda.findData(eda_win)
        if idx >= 0: self.combo_eda.setCurrentIndex(idx)

        self.combo_ppg = QComboBox()
        self.combo_ppg.setToolTip("Time window for Heart Rate calculation")
        for w in [5, 10, 20, 30, 60]:
            self.combo_ppg.addItem(f"{w} s", w)
        idx = self.combo_ppg.findData(ppg_win)
        if idx >= 0: self.combo_ppg.setCurrentIndex(idx)

        self.combo_hrv = QComboBox()
        self.combo_hrv.setToolTip("Time window for HRV (RMSSD) calculation")
        for w in [30, 60, 120, 300]:
            self.combo_hrv.addItem(f"{w} s", w)
        idx = self.combo_hrv.findData(hrv_win)
        if idx >= 0: self.combo_hrv.setCurrentIndex(idx)
            
        form.addRow("Sampling Rate:", self.combo_rate)
        form.addRow("EDA Window:", self.combo_eda)
        form.addRow("PPG Window:", self.combo_ppg)
        form.addRow("HRV Window:", self.combo_hrv)
        grp.setLayout(form)
        self.layout_main.addWidget(grp)
        
        self.layout_main.addStretch()
        
        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("secondary")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_apply = QPushButton("Apply")
        self.btn_apply.clicked.connect(self.accept)
        
        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_apply)
        self.layout_main.addLayout(btn_box)
        
    def get_selected_rate(self):
        return self.combo_rate.currentData()

    def get_windows(self):
        return self.combo_eda.currentData(), self.combo_ppg.currentData(), self.combo_hrv.currentData()

class RibbonButton(QToolButton):
    def __init__(self, text, icon_std_key, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if isinstance(icon_std_key, QIcon):
             self.setIcon(icon_std_key)
        else:
            self.setIcon(parent.style().standardIcon(icon_std_key))
        self.setIconSize(QSize(28, 28))
        self.setFixedSize(110, 85)
        self.setAutoRaise(True)
        self.setStyleSheet(f"""
            QToolButton {{
                border-radius: 8px; 
                padding: 5px;
                color: {COLOR_TEXT};
                font-weight: 500;
            }}
            QToolButton:hover {{
                background: #EFEFEF;
                border: 1px solid #CCC;
            }}
            QToolButton:pressed {{
                background: #DDD;
            }}
        """)

# --- GRAPH WIDGET ---
class BioSignalPlot(QWidget):
    def __init__(self, title, left_label, left_unit, right_label=None, right_unit=None):
        super().__init__()
        self.main_layout = QVBoxLayout(self) # type: ignore
        self.main_layout.setContentsMargins(0, 0, 0, 0) # type: ignore
        
        # Configuration
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=True)

        self.plot_widget = pg.PlotWidget(title=title)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.plotItem.setMouseEnabled(x=True, y=False)
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush(255,255,255,200)) # Semi-transparent white
        self.plot_widget.setLabel('bottom', "Time", units='s')
        self.plot_widget.setLabel('left', left_label, units=left_unit)
        
        self.main_layout.addWidget(self.plot_widget)
        
        # Data Containers (Strip Chart Logic)
        self.buffer_size = 300
        self.fs = 20.0 # Hz
        # X-Data will hold actual timestamps (simulated)
        self.x_data = np.array([])
        
        self.dual_axis = right_label is not None
        
        # --- LEFT AXIS (Primary) ---
        # Determining Colors based on label for strict requirement matching
        if "EDA" in left_label:
            c1 = COLOR_EDA
            name1 = left_label
        elif "Phasic" in left_label:
            c1 = COLOR_EDA
            name1 = left_label
        else:
            c1 = COLOR_PRIMARY
            name1 = left_label

        self.data1 = np.array([])
        self.curve1 = self.plot_widget.plot(self.x_data, self.data1, pen=pg.mkPen(c1, width=2), name=name1)

        # --- RIGHT AXIS (Secondary) or SAME AXIS ---
        if self.dual_axis:
            # Setup ViewBox for Right Axis
            self.plot_item = self.plot_widget.plotItem
            self.vb2 = pg.ViewBox()
            self.vb2.setMouseEnabled(x=True, y=False)
            self.plot_item.showAxis('right')
            self.plot_item.scene().addItem(self.vb2)
            self.plot_item.getAxis('right').linkToView(self.vb2)
            self.vb2.setXLink(self.plot_item)
            self.plot_item.getAxis('right').setLabel(right_label, units=right_unit)
            
            self.data2 = np.array([])
            # HR is Red
            c2 = COLOR_HR if "Heart" in right_label else COLOR_RECORD
            
            self.curve2 = pg.PlotCurveItem(self.x_data, self.data2, pen=pg.mkPen(c2, width=2, style=Qt.DashLine), name=right_label)
            self.vb2.addItem(self.curve2)
            
            # Add to legend manually since it's on a different viewbox
            self.legend.addItem(self.curve2, right_label)
            
            self.plot_item.vb.sigResized.connect(self.update_views)
        else:
            # Same axis (Bottom Graph: Phasic vs Tonic)
            self.data2 = np.array([])
            # Tonic is Gold
            c2 = COLOR_TONIC
            self.curve2 = self.plot_widget.plot(self.x_data, self.data2, pen=pg.mkPen(c2, width=2), name="Tonic Level")

    def update_views(self):
        if self.dual_axis:
            self.vb2.setGeometry(self.plot_item.vb.sceneBoundingRect())
            self.vb2.linkedViewChanged(self.plot_item.vb, self.vb2.XAxis)

    def reset_data(self):
        self.x_data = np.array([])
        self.data1 = np.array([])
        self.data2 = np.array([])
        self.curve1.setData(self.x_data, self.data1)
        self.curve2.setData(self.x_data, self.data2)
        # Clear lines
        for item in self.plot_widget.items():
            if isinstance(item, pg.InfiniteLine):
                self.plot_widget.removeItem(item)

    def add_marker(self, text, color_hex):
        """Adds a marker at the current latest timestamp (right side)"""
        if len(self.x_data) > 0:
            current_time = self.x_data[-1]
        else:
            current_time = 0.0
        c = QColor(color_hex)
        
        # InfiniteLine at current_time. 
        # Since we use real coordinates for X, the line will stay at this X value
        # while the View moves or data updates.
        line = pg.InfiniteLine(pos=current_time, angle=90, pen=pg.mkPen(c, width=2, style=Qt.DashDotLine), 
                               label=text, labelOpts={'color': COLOR_TEXT, 'position': 0.8, 'fill': (255,255,255,200)})
        
        self.plot_widget.addItem(line)
        return line

    def remove_marker(self, line_obj):
        self.plot_widget.removeItem(line_obj)

    def push_data(self, val1, val2):
        """Updates the plot with new real data points"""
        # Shift Time Window
        dt = 1.0 / self.fs
        
        if len(self.x_data) > 0:
            new_time = self.x_data[-1] + dt
        else:
            new_time = 0.0
        
        self.x_data = np.append(self.x_data, new_time)
        self.data1 = np.append(self.data1, val1)
        self.data2 = np.append(self.data2, val2)
        
        if len(self.x_data) > self.buffer_size:
            self.x_data = self.x_data[-self.buffer_size:]
            self.data1 = self.data1[-self.buffer_size:]
            self.data2 = self.data2[-self.buffer_size:]
        
        # Update Curves
        self.curve1.setData(self.x_data, self.data1)
        self.curve2.setData(self.x_data, self.data2)

    def push_data_batch(self, val1_list, val2_list):
        """Updates the plot with a batch of new data points"""
        n = len(val1_list)
        if n == 0: return
        
        # Shift Time Window
        dt = 1.0 / self.fs
        
        # Generate new time points extending from the last known time
        if len(self.x_data) > 0:
            last_time = self.x_data[-1]
        else:
            last_time = -dt # So first point starts at 0
            
        new_times = last_time + np.arange(1, n + 1) * dt
        
        # Append
        self.x_data = np.concatenate([self.x_data, new_times])
        self.data1 = np.concatenate([self.data1, val1_list])
        self.data2 = np.concatenate([self.data2, val2_list])
        
        # Slice if needed
        if len(self.x_data) > self.buffer_size:
            self.x_data = self.x_data[-self.buffer_size:]
            self.data1 = self.data1[-self.buffer_size:]
            self.data2 = self.data2[-self.buffer_size:]
        
        # Update Curves
        self.curve1.setData(self.x_data, self.data1)
        self.curve2.setData(self.x_data, self.data2)

# --- MAIN WINDOW ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drexel EDA Lab Platform [Research Grade]")
        self.resize(1400, 950)
        
        # State
        self.device_connected = False
        self.ingestion_thread = None
        self.last_hardware_error = None
        self.is_recording = False
        self.is_paused = True
        self.active_flags = [] # Stores dicts of {timestamp, line_obj, list_item}
        self.sampling_rate = 20 # Default
        
        # --- DATA PROCESSORS ---
        self.eda_processor = EDAProcessor(self, sampling_rate=self.sampling_rate)
        self.ppg_processor = PPGProcessor(self, sampling_rate=self.sampling_rate)
        self.hrv_processor = HRVProcessor(sampling_rate=self.sampling_rate, window_second=30, parent=self)
        self.hrv_processor.hrv_computed.connect(self.on_hrv_update)
        self._hrv_windows = []
        
        # Data Buffer for UI Throttling
        self.packet_buffer = []
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_ui_from_buffer)
        self.ui_update_timer.start(33) # ~30 FPS
        
        # Connection Timeout Timer
        self.conn_timer = QTimer(self)
        self.conn_timer.setSingleShot(True)
        self.conn_timer.timeout.connect(self.on_connection_timeout)

        # Time elapsed Timer
        self.session_start_time = None
        self.timer_elapsed = QTimer(self)
        self.timer_elapsed.timeout.connect(self.update_elapsed_time)


        QApplication.instance().setStyleSheet(ResearchStyleSheet.get_stylesheet())
        self.setup_ui()

    def setup_ui(self):
        self.create_menu_bar()
        
        central = QWidget()
        self.setCentralWidget(central)
        main_v = QVBoxLayout(central)
        main_v.setContentsMargins(0,0,0,0)
        main_v.setSpacing(0)
        
        # 1. Ribbon
        self.create_ribbon()
        main_v.addWidget(self.ribbon_tabs)
        
        # 2. Workspace
        workspace = QHBoxLayout()
        workspace.setContentsMargins(10,10,10,10)
        workspace.setSpacing(15)
        
        self.create_left_panel()
        self.create_center_stage()
        self.create_right_panel()
        
        workspace.addWidget(self.panel_left, 1)
        workspace.addWidget(self.center_stack, 4)
        workspace.addWidget(self.panel_right, 1)
        
        main_v.addLayout(workspace)
        
        # 3. Status Bar
        self.create_status_bar()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Session", lambda: self.on_start_session() if self.device_connected else None)
        file_menu.addAction("Open Session...", self.on_load_clicked)
        file_menu.addAction("Import Subject Data...", self.on_import_subject)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Documentation")
        help_menu.addAction("About")

    def create_ribbon(self):
        self.ribbon_tabs = QTabWidget()
        self.ribbon_tabs.setMinimumHeight(140)
        self.ribbon_tabs.setMaximumHeight(150)
        
        def create_page(buttons_config):
            page = QWidget()
            layout = QHBoxLayout(page)
            layout.setAlignment(Qt.AlignLeft)
            layout.setContentsMargins(10,10,10,10)
            layout.setSpacing(10)
            for btn_text, icon_key, func in buttons_config:
                btn = RibbonButton(btn_text, icon_key, self)
                if func: btn.clicked.connect(func)
                layout.addWidget(btn)
            return page

        # GROUP 1: SETUP
        setup_page = create_page([
            ("Connect\nDevice", QStyle.SP_ComputerIcon, self.on_connect_request),
            ("Subject\nData", QStyle.SP_FileDialogInfoView, self.open_subject_data_dialog),
            ("Hardware\nDiagnostics", pg.QtWidgets.QStyle.SP_DriveHDIcon, self.open_diagnostics)
        ])
        self.ribbon_tabs.addTab(setup_page, "Setup")

        # GROUP 2: RECORDING
        # Using built-in icons to approximate Gear/Waveform
        acq_page = create_page([
            ("Hardware\nConfig", QStyle.SP_FileDialogDetailedView, self.open_hardware_config), # Gear-ish
            ("Noise\nThresholds", QStyle.SP_DriveNetIcon, None), # Waveform-ish
            ("Activity\nProfile", QStyle.SP_MediaSeekForward, self.open_activity_profile) # Motion-ish
        ])
        self.ribbon_tabs.addTab(acq_page, "Recording")

        
        # GROUP 3: ANALYSIS
        ana_page = create_page([
            ("Run\ncvxEDA", QStyle.SP_MediaPlay, lambda: QMessageBox.information(self, "Info", "Optimization Started")),
            ("Filter\nConfig", QStyle.SP_FileDialogListView, None),
            ("HRV\nDashboard", QStyle.SP_FileDialogContentsView, lambda: QMessageBox.information(self, "HRV", "Opening HRV Dashboard...")),
            ("NK2\nVerify", QStyle.SP_ComputerIcon, lambda: self.eda_processor.create_debug_plot())
        ])
        self.ribbon_tabs.addTab(ana_page, "Analysis")

        # GROUP 4: HRV
        # Clicking on the buttons opens a separate window with an interactive graph
        hrv_page = create_page([
            #("Run\nRMSSD", QStyle.SP_FileDialogDetailedView, self._hrv_run_rmssd),
            ("Display\nR-R intervals", QStyle.SP_FileDialogDetailedView, self._hrv_open_rri),
            ("Display\nPoincare Plot", QStyle.SP_FileDialogDetailedView,  self._hrv_open_poincare),
            ("Display\nPSD", QStyle.SP_FileDialogDetailedView, self._hrv_open_psd),
        ])
        self.ribbon_tabs.addTab(hrv_page, "HRV") 
        
        # GROUP 5: EXPORT
        exp_page = create_page([
            ("Export\nCSV", QStyle.SP_FileIcon, lambda: print("Exporting CSV...")),
            ("Save Graph\nImage", QStyle.SP_DialogSaveButton, lambda: print("Saving Image...")),
            ("Generate\nLab Report", QStyle.SP_MessageBoxInformation, lambda: print("Generating Report..."))
        ])
        self.ribbon_tabs.addTab(exp_page, "Export")

    def create_left_panel(self):
        self.panel_left = QWidget()
        self.panel_left.setFixedWidth(280)
        layout = QVBoxLayout(self.panel_left)
        layout.setContentsMargins(0,0,0,0)
        
        # Session Info
        grp_sub = QGroupBox("Subject Data")
        gl = QGridLayout()
        
        gl.addWidget(QLabel("Name:"), 0, 0)
        self.txt_sub_name = QLineEdit()
        self.txt_sub_name.setReadOnly(True)
        gl.addWidget(self.txt_sub_name, 0, 1)

        gl.addWidget(QLabel("ID:"), 1, 0)
        self.txt_sub_id = QLineEdit()
        self.txt_sub_id.setReadOnly(True)
        gl.addWidget(self.txt_sub_id, 1, 1)
        
        gl.addWidget(QLabel("Sex:"), 2, 0)
        self.txt_sub_sex = QLineEdit()
        self.txt_sub_sex.setReadOnly(True)
        gl.addWidget(self.txt_sub_sex, 2, 1)

        gl.addWidget(QLabel("Age: "), 3, 0)
        self.txt_sub_age = QLineEdit()
        self.txt_sub_age.setReadOnly(True)
        gl.addWidget(self.txt_sub_age, 3, 1)

        gl.addWidget(QLabel("Ethnicity:"), 4, 0)
        self.txt_sub_ethnicity = QLineEdit()
        self.txt_sub_ethnicity.setReadOnly(True)
        gl.addWidget(self.txt_sub_ethnicity, 4, 1)

        gl.addWidget(QLabel("Handedness:"), 5, 0)
        self.txt_sub_handedness = QLineEdit()
        self.txt_sub_handedness.setReadOnly(True)
        gl.addWidget(self.txt_sub_handedness, 5, 1)

        gl.addWidget(QLabel("Notes:"), 6, 0)
        self.txt_sub_notes = QTextEdit()
        self.txt_sub_notes.setReadOnly(True)
        self.txt_sub_notes.setMaximumHeight(50)
        gl.addWidget(self.txt_sub_notes, 6, 1)

        gl.addWidget(QLabel("Session:"), 7, 0)
        self.txt_session = QLineEdit("001")
        gl.addWidget(self.txt_session, 7, 1)
        
        grp_sub.setLayout(gl)
        layout.addWidget(grp_sub)
        
        # Device Status
        grp_dev = QGroupBox("Device Status")
        dl = QVBoxLayout()
        self.lbl_conn = QLabel("DISCONNECTED")
        self.lbl_conn.setAlignment(Qt.AlignCenter)
        self.lbl_conn.setStyleSheet("color: #777; border: 2px dashed #CCC; padding: 15px; border-radius: 8px;")
        dl.addWidget(self.lbl_conn)
        
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self.on_disconnect)
        dl.addWidget(self.btn_disconnect)
        
        grp_dev.setLayout(dl)
        layout.addWidget(grp_dev)
        
        # Recording Button
        grp_rec = QGroupBox("Recording Control")
        rl = QVBoxLayout()
        self.btn_rec = QPushButton("REC")
        self.btn_rec.setCheckable(True)
        self.btn_rec.setFixedSize(100, 100)
        self.btn_rec.setEnabled(False)
        self.btn_rec.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #F0F0F0; 
                border-radius: 50px; 
                border: 4px solid #CCC; 
                color: #AAA; 
                font-size: 18pt; 
                font-weight: 900; 
            }}
            QPushButton:checked {{ 
                background-color: {COLOR_RECORD}; 
                border-color: {COLOR_PRIMARY}; 
                color: white; 
                border: 4px solid {COLOR_PRIMARY};
            }}
        """)
        self.btn_rec.toggled.connect(self.on_record_toggled)
        
        h = QHBoxLayout()
        h.addStretch(); h.addWidget(self.btn_rec); h.addStretch()
        rl.addLayout(h)
        
        self.lbl_rec_hint = QLabel("Ready")
        self.lbl_rec_hint.setAlignment(Qt.AlignCenter)
        rl.addWidget(self.lbl_rec_hint)
        
        # --- Playback Controls ---
        playback_layout = QHBoxLayout()
        playback_layout.setSpacing(5)
        
        self.btn_sim_start = QPushButton("Start")
        self.btn_sim_start.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_sim_start.clicked.connect(self.on_start_sim)
        self.btn_sim_start.setEnabled(False)
        
        self.btn_sim_pause = QPushButton("Pause")
        self.btn_sim_pause.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.btn_sim_pause.clicked.connect(self.on_pause_sim)
        self.btn_sim_pause.setEnabled(False)
        
        self.btn_sim_stop = QPushButton("Stop")
        self.btn_sim_stop.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.btn_sim_stop.clicked.connect(self.on_stop_sim)
        self.btn_sim_stop.setEnabled(False)
        
        for btn in [self.btn_sim_start, self.btn_sim_pause, self.btn_sim_stop]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_BG_WHITE};
                    color: {COLOR_PRIMARY};
                    border: 1px solid {COLOR_PRIMARY};
                    border-radius: 8px;
                    padding: 6px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #E0E0E0;
                }}
            """)
            playback_layout.addWidget(btn)
            
        rl.addLayout(playback_layout)
        
        grp_rec.setLayout(rl)
        layout.addWidget(grp_rec)
        
        layout.addStretch()

    def create_center_stage(self):
        self.center_stack = QStackedWidget()
        
        # Page 0: Dashboard
        p_dash = QWidget()
        l_dash = QVBoxLayout(p_dash)
        l_dash.setAlignment(Qt.AlignCenter)
        
        title = QLabel("EDA Research Platform")
        title.setFont(QFont(FONT_UI, 32, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLOR_PRIMARY}")
        
        self.btn_start = QPushButton("Start New Session")
        self.btn_start.setFixedSize(300, 70)
        self.btn_start.setEnabled(False) # Strict logic
        self.btn_start.setStyleSheet(f"""
            QPushButton {{ font-size: 14pt; }}
            QPushButton:disabled {{ background-color: #DDD; color: #999; }}
        """)
        self.btn_start.clicked.connect(self.on_start_session)
        
        btn_load = QPushButton("Load Previous Data")
        btn_load.setObjectName("secondary")
        btn_load.setFixedSize(300, 70)
        btn_load.clicked.connect(self.on_load_clicked)
        
        l_dash.addWidget(title)
        l_dash.addSpacing(50)
        l_dash.addWidget(self.btn_start)
        l_dash.addSpacing(20)
        l_dash.addWidget(btn_load)
        
        self.center_stack.addWidget(p_dash)
        
        # Page 1: Live View
        p_live = QWidget()
        l_live = QVBoxLayout(p_live)
        
        # Top Graph: Dual Axis (EDA + HR)
        self.graph_main = BioSignalPlot("Live Physiological Signals (EDA | HR)", "EDA", "µS", "Heart Rate", "BPM")
        l_live.addWidget(self.graph_main, 5)
        
        # Bottom Graph: Decomposition
        self.graph_sub = BioSignalPlot("Signal Decomposition (Phasic | Tonic)", "Phasic Driver", "µS")
        l_live.addWidget(self.graph_sub, 3)
        
        # Event Insertion Bar
        f_evt = QFrame()
        f_evt.setObjectName("event_bar")
        hl = QHBoxLayout(f_evt)
        
        hl.addWidget(QLabel("Event Label:"))
        self.txt_event = QLineEdit()
        self.txt_event.setPlaceholderText("e.g. Stressor Start")
        hl.addWidget(self.txt_event)
        
        btn_insert = QPushButton("Insert Event")
        btn_insert.setObjectName("secondary") # Gray
      
        btn_insert.clicked.connect(lambda: self.on_insert_event())
        hl.addWidget(btn_insert)

        for key, label in [("F1", "Task Start"), ("F2", "Event"), ("F3", "Recovery")]:
            btn = QPushButton(f"{key}: {label}")
            btn.setObjectName("secondary")
            btn.clicked.connect(lambda checked=False, l=label: self.on_insert_event(l))
            hl.addWidget(btn)
        
        l_live.addWidget(f_evt)
        self.center_stack.addWidget(p_live)

    def create_right_panel(self):
        self.panel_right = QWidget()
        self.panel_right.setFixedWidth(300)
        layout = QVBoxLayout(self.panel_right)
        layout.setContentsMargins(0,0,0,0)
        
        # Live Metrics
        grp_met = QGroupBox("Live Metrics")
        hl = QHBoxLayout()
        
        # EDA Column
        v_eda = QVBoxLayout()
        v_eda.addWidget(QLabel("Skin Conductance:"))
        self.val_eda = QLabel("-- µS")
        self.val_eda.setFont(QFont(FONT_MONO, 24, QFont.Bold))
        self.val_eda.setStyleSheet(f"color: {COLOR_EDA}")
        v_eda.addWidget(self.val_eda)
        
        # HR Column
        v_hr = QVBoxLayout()
        v_hr.addWidget(QLabel("Heart Rate:"))
        self.val_hr = QLabel("-- BPM")
        self.val_hr.setFont(QFont(FONT_MONO, 24, QFont.Weight.Bold)) # type: ignore
        self.val_hr.setStyleSheet(f"color: {COLOR_HR}")
        v_hr.addWidget(self.val_hr)
        
        # HRV Column
        v_hrv = QVBoxLayout()
        v_hrv.addWidget(QLabel("HRV (RMSSD):"))
        self.val_hrv = QLabel("-- ms")
        self.val_hrv.setFont(QFont(FONT_MONO, 24, QFont.Weight.Bold))
        self.val_hrv.setStyleSheet(f"color: {COLOR_TEXT}")
        v_hrv.addWidget(self.val_hrv)

        #Time Column
        v_time = QVBoxLayout()
        v_time.addWidget(QLabel("Time:"))
        self.val_time = QLabel("--:--")
        self.val_time.setFont(QFont(FONT_MONO, 24, QFont.Weight.Bold))
        self.val_time.setStyleSheet(f"color: {COLOR_TEXT}")
        v_time.addWidget(self.val_time)
        
        hl.addLayout(v_eda)
        hl.addLayout(v_hr)
        hl.addLayout(v_hrv)
        hl.addLayout(v_time)
        grp_met.setLayout(hl)
        layout.addWidget(grp_met)        
        
        # Flag Management
        grp_flag = QGroupBox("Flag Management")
        fl = QVBoxLayout()
        
        self.list_flags = QListWidget()
        fl.addWidget(self.list_flags)
        
        btn_del = QPushButton("Delete Selected")
        btn_del.setObjectName("secondary")
        btn_del.clicked.connect(self.on_delete_flag)
        
        btn_exp = QPushButton("Export Selection")
        btn_exp.setObjectName("secondary")
        
        fl.addWidget(btn_del)
        fl.addWidget(btn_exp)
        grp_flag.setLayout(fl)
        layout.addWidget(grp_flag)
        
        layout.addStretch()

    def update_elapsed_time(self):
        if not self.session_start_time:
            return
        elapsed = datetime.datetime.now() - self.session_start_time
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        self.val_time.setText(f"{minutes:02d}:{seconds:02d}")

    # --- LOGIC ---
    def on_connect_request(self):
        dlg = ConnectDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_port:
            # Stop existing thread
            if self.ingestion_thread and self.ingestion_thread.isRunning():
                self.ingestion_thread.stop()
            
            self.device_connected = True
            self.last_hardware_error = None
            self.is_paused = True
            
            try:
                if dlg.debug_mode:
                    self.ingestion_thread = SimulationIngestionThread(sampling_rate=self.sampling_rate)
                    # Immediate UI update for simulation
                    self.lbl_conn.setText("CONNECTED (SIM)")
                    self.lbl_conn.setStyleSheet("color: green; border: 2px solid green; font-weight: bold; border-radius: 8px; background: #E8F5E9;")
                    self.btn_start.setEnabled(True)
                    self.btn_start.setText("Start Live Session")
                    self.btn_disconnect.setEnabled(True)
                    self.statusBar().showMessage("Simulation Stream Active.")
                else:
                    self.ingestion_thread = HardwareIngestionThread(port=dlg.selected_port)
                    self.lbl_conn.setText("CONNECTING...")
                    self.lbl_conn.setStyleSheet("color: orange; border: 2px dashed orange; padding: 15px; border-radius: 8px;")
                    self.statusBar().showMessage("Attempting connection to hardware...")
                    # Start Timeout Timer (5 seconds)
                    self.conn_timer.start(5000)
                
                self.ingestion_thread.packet_ready.connect(self.on_packet_received)
                self.ingestion_thread.error_occurred.connect(self.on_hardware_error)
                self.ingestion_thread.start()
            except Exception as e:
                self.on_hardware_error(f"Failed to start ingestion: {e}")

    def on_disconnect(self):
        self.conn_timer.stop()
        if self.ingestion_thread:
            self.ingestion_thread.stop()
            self.ingestion_thread = None
            
        self.device_connected = False
        self.is_paused = True
        self.lbl_conn.setText("DISCONNECTED")
        self.lbl_conn.setStyleSheet("color: #777; border: 2px dashed #CCC; padding: 15px; border-radius: 8px;")
        
        self.btn_start.setEnabled(False)
        self.btn_start.setText("Start New Session")
        self.btn_disconnect.setEnabled(False)
        
        # Disable Recording Controls
        if self.btn_rec.isChecked():
            self.btn_rec.setChecked(False)
        self.btn_rec.setEnabled(False)
        self.btn_sim_start.setEnabled(False)
        self.btn_sim_pause.setEnabled(False)
        self.btn_sim_stop.setEnabled(False)
        self.statusBar().showMessage("Device Disconnected.")

    def on_packet_received(self, packet: SensorPacket):
        # If this is the first packet, confirm connection in UI
        if "CONNECTING" in self.lbl_conn.text():
            self.conn_timer.stop()
            self.lbl_conn.setText("CONNECTED")
            self.lbl_conn.setStyleSheet("color: green; border: 2px solid green; font-weight: bold; border-radius: 8px; background: #E8F5E9;")
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Start Live Session")
            self.btn_disconnect.setEnabled(True)
            self.statusBar().showMessage("Hardware Stream Active.")

        if self.is_paused:
            return
        self.packet_buffer.append(packet)

    def update_ui_from_buffer(self):
        if not self.packet_buffer:
            return
            
        packets = self.packet_buffer
        self.packet_buffer = []

        # 1. Pass data to processors
        # EDA & Decomposition
        eda_batch, phasic_batch, tonic_batch = self.eda_processor.process_batch(packets)
        
        # PPG / Heart Rate
        hr_batch = self.ppg_processor.process_batch(packets)
        
        # HRV (Process individually as it maintains internal buffer state)
        for packet in packets:
            self.hrv_processor.process_packet(packet)
            
        # Update Metrics (Last value)
        self.val_eda.setText(f"{eda_batch[-1]:.2f} µS")
        self.val_hr.setText(f"{int(hr_batch[-1])} BPM")
        
        # Update Graphs
        self.graph_main.push_data_batch(eda_batch, hr_batch)
        self.graph_sub.push_data_batch(phasic_batch, tonic_batch)

    def on_hrv_update(self, data):
        if "rmssd" in data:
            self.val_hrv.setText(f"{data['rmssd']:.1f} ms")

    def _hrv_check_data_ready(self):
        if len(self.hrv_processor._rri_ms) < 2:
            QMessageBox.warning(self, "Insufficient Data", "Not enough RR intervals to plot.")
            return False
        return True
    
    def _hrv_run_rmssd(self):
        if len(self.hrv_processor._rri_ms) < 2:
            QMessageBox.warning(self, "Insufficient Data", "Not enough RR intervals to plot.")
            return
        self.hrv_processor.compute_hrv()
        self.statusBar().showMessage("HRV (RMSSD) Computed.", 3000)

    def _hrv_open_rri(self):
        if self._hrv_check_data_ready():
            self._hrv_windows.append(self.hrv_processor.open_rri_window())

    def _hrv_open_poincare(self):
        if self._hrv_check_data_ready():
            self._hrv_windows.append(self.hrv_processor.open_poincare_window())
    
    def _hrv_open_psd(self):
        if self._hrv_check_data_ready():
            self._hrv_windows.append(self.hrv_processor.open_psd_window())

    def on_connection_timeout(self):
        if "CONNECTING" in self.lbl_conn.text():
            self.on_hardware_error("Connection timed out: No data received within 5 seconds.")

    def on_hardware_error(self, msg: str):
        self.last_hardware_error = msg
        self.on_disconnect() # Clean up thread and UI state
        
        # Override status to show error
        self.lbl_conn.setText("CONNECTION ERROR")
        self.lbl_conn.setStyleSheet(f"color: {COLOR_RECORD}; border: 2px solid {COLOR_RECORD}; font-weight: bold; border-radius: 8px; background: #FDEDEC;")
        self.statusBar().showMessage(f"Hardware Error: {msg}")
        QMessageBox.critical(self, "Hardware Error", f"Connection lost: {msg}")

    def on_start_session(self):
        if not self.device_connected: return
        
        # Enable Recording Controls
        self.btn_rec.setEnabled(True)
        
        # Start in PAUSED state so user must click Start
        self.is_paused = True
        self.btn_sim_start.setEnabled(True)
        self.btn_sim_pause.setEnabled(False)
        self.btn_sim_stop.setEnabled(True)
        
        # Switch View
        self.center_stack.setCurrentIndex(1)
        
        # Reset Graphs
        self.graph_main.reset_data()
        self.graph_sub.reset_data()

        # Start timer
        self.session_start_time = datetime.datetime.now()
        self.timer_elapsed.start(1000)
        
        self.statusBar().showMessage("Session Ready. Press Start to begin data stream.")

    def on_load_clicked(self):
        QFileDialog.getOpenFileName(self, "Load Data", "", "CSV Files (*.csv)")

    def on_record_toggled(self, checked):
        self.is_recording = checked
        if checked:
            self.lbl_rec_hint.setText("RECORDING")
            self.lbl_rec_hint.setStyleSheet(f"color: {COLOR_RECORD}; font-weight: bold;")
        else:
            self.lbl_rec_hint.setText("Ready")
            self.lbl_rec_hint.setStyleSheet("color: black;")
        
        print("Recording State Toggled")

    def on_insert_event(self, label=None):
        if label is None:
            label = self.txt_event.text() or "Event"
            self.txt_event.clear()
        
        # Random Color
        color = "#" + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
        
        # Add to Graphs (Top and Bottom)
        l1 = self.graph_main.add_marker(label, color)
        l2 = self.graph_sub.add_marker(label, color)
        
        # Add to List
        # Get timestamp from graph
        if len(self.graph_main.x_data) > 0:
            ts = self.graph_main.x_data[-1]
        else:
            ts = 0.0
        ts_fmt = f"{ts:.2f}s"
        
        item = pg.QtWidgets.QListWidgetItem(f"[{ts_fmt}] {label}")
        item.setForeground(QColor(color))
        self.list_flags.addItem(item)
        
        self.active_flags.append({
            'line_main': l1,
            'line_sub': l2,
            'item': item
        })

    def update_status_bar_stats(self):
        # Time
        self.lbl_time.setText(f"System Time: {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        # Hardware Stats
        try:
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            self.lbl_disk.setText(f"Disk: {free_gb:.1f}GB Free")
            
            ram = psutil.virtual_memory()
            self.lbl_ram.setText(f"RAM: {ram.percent}% Used")
            
            cpu = psutil.cpu_percent()
            self.lbl_cpu.setText(f"CPU: {cpu}%")
        except Exception:
            pass

    def create_status_bar(self):

        status = QStatusBar()

        self.setStatusBar(status)
        status.showMessage("System Ready - Connect Device to Begin")

        

        # Permanent widgets

        self.lbl_cpu = QLabel("CPU: --")
        self.lbl_disk = QLabel("Disk: --")
        self.lbl_ram = QLabel("RAM: --")
        self.lbl_time = QLabel()

        

        status.addPermanentWidget(self.lbl_cpu)
        status.addPermanentWidget(self.lbl_disk)

        status.addPermanentWidget(self.lbl_ram)

        status.addPermanentWidget(self.lbl_time)

        

        # Update time
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status_bar_stats)
        self.status_timer.start(1000)
        self.update_status_bar_stats()



    def on_delete_flag(self):
        row = self.list_flags.currentRow()
        if row >= 0:
            target = self.active_flags.pop(row)
            
            # Remove lines
            self.graph_main.remove_marker(target['line_main'])
            self.graph_sub.remove_marker(target['line_sub'])
            
            # Remove list item
            self.list_flags.takeItem(row)

    def on_start_sim(self):
        self.is_paused = False
        self.btn_sim_start.setEnabled(False)
        self.btn_sim_pause.setEnabled(True)
        self.statusBar().showMessage("Data Stream Resumed.")

    def on_pause_sim(self):
        self.is_paused = True
        self.btn_sim_start.setEnabled(True)
        self.btn_sim_pause.setEnabled(False)
        self.statusBar().showMessage("Data Stream Paused.")

    def on_stop_sim(self):
        dlg = ExitDialog(self, "End Session?", "End Session", "Do you want to save the session data?")
        if dlg.exec() == QDialog.Accepted:
            if dlg.action == 'save':
                print("Saving Session Data...") # Placeholder
            self.on_disconnect()
            self.center_stack.setCurrentIndex(0) # Return to dashboard

    def closeEvent(self, event):
        dlg = ExitDialog(self)
        if dlg.exec() == QDialog.Accepted:
            if dlg.action == 'save':
                print("Saving...")
            elif dlg.action == 'discard':
                print("Discarding...")
            
            # Stop Timers
            if self.conn_timer.isActive():
                self.conn_timer.stop()

            if self.timer_elapsed.isActive():
                self.timer_elapsed.stop()
            
            # Stop Thread
            if self.ingestion_thread:
                # stop() handles the wait() call internally
                self.ingestion_thread.stop()
            event.accept()
        else:
            event.ignore()
    def open_subject_data_dialog(self):
        dialog = SubjectDataDialog(self)
        if dialog.exec():
            # If data was saved, populate the left panel
            if dialog.saved_data:
                # Unpack new schema: (id, subject_id, name, age, sex, ethnicity, handedness, notes)
                data = dialog.saved_data
                # Handle potential legacy data or new data safely
                if len(data) >= 8:
                    sid, subject_id, name, age, sex, ethnicity, handedness, notes = data
                    self.txt_sub_id.setText(subject_id)
                    self.txt_sub_name.setText(name)
                    self.txt_sub_sex.setText(sex)
                    self.txt_sub_age.setText(str(age))
                    self.txt_sub_ethnicity.setText(ethnicity)
                    self.txt_sub_handedness.setText(handedness)
                    self.txt_sub_notes.setText(notes)

            self.statusBar().showMessage("Subject metadata updated successfully.", 5000)

    def on_import_subject(self):
        dlg = SubjectSelectionDialog(self)
        if dlg.exec():
            sub = dlg.selected_subject
            if sub:
                # sub is tuple: (id, subject_id, name, age, sex, ethnicity, handedness, notes)
                self.txt_sub_id.setText(sub[1])
                self.txt_sub_name.setText(sub[2])
                self.txt_sub_sex.setText(sub[4])
                self.txt_sub_age.setText(str(sub[3]))
                self.txt_sub_ethnicity.setText(sub[5])
                self.txt_sub_handedness.setText(sub[6])
                self.txt_sub_notes.setText(sub[7])
                self.statusBar().showMessage(f"Imported subject: {sub[2]}")

    def open_diagnostics(self):
        dlg = HardwareDiagnosticsDialog(self, active_error=self.last_hardware_error)
        dlg.exec()

    def open_activity_profile(self):
        dlg = ActivityProfileDialog(self)
        dlg.exec()
        
    def open_hardware_config(self):
        # Get current values
        eda_win = self.eda_processor.window_seconds
        ppg_win = self.ppg_processor.window_seconds
        hrv_win = self.hrv_processor.window_second

        dlg = HardwareConfigDialog(self.sampling_rate, eda_win, ppg_win, hrv_win, self)
        if dlg.exec() == QDialog.Accepted:
            new_rate = dlg.get_selected_rate()
            new_eda, new_ppg, new_hrv = dlg.get_windows()
            
            if new_rate != self.sampling_rate:
                self.sampling_rate = new_rate
                self.eda_processor.set_sampling_rate(new_rate)
                self.ppg_processor.set_sampling_rate(new_rate)
                self.hrv_processor.set_sampling_rate(new_rate)
                self.graph_main.fs = float(new_rate)
                self.graph_sub.fs = float(new_rate)
            
            self.eda_processor.set_window_seconds(new_eda)
            self.ppg_processor.set_window_seconds(new_ppg)
            self.hrv_processor.set_window_seconds(new_hrv)
            
            self.statusBar().showMessage(f"Acquisition settings updated: {new_rate}Hz")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())