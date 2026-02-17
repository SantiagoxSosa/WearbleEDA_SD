from database import SubjectDataDialog, SubjectSelectionDialog
from colorconstraints import *

import sys
import datetime
import random
import numpy as np
import psutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                               QGroupBox, QFrame, QStatusBar, QMenuBar, QMenu, 
                               QDialog, QListWidget, QStackedWidget, QMessageBox,
                               QGridLayout, QTabWidget, QToolButton, QFileDialog, QTextEdit,
                               QSizePolicy, QSplitter, QAbstractItemView, QStyle)
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
        super().__init__("Bluetooth Device Discovery", parent)
        self.setFixedSize(450, 350)
        
        header = QLabel("Available Bio-Sensors")
        header.setObjectName("h1")
        self.layout_main.addWidget(header)
        
        self.list_widget = QListWidget()
        self.list_widget.addItems([
            "EDA_DEVICE_A1", 
            "EDA_DEVICE_B2"
        ])
        self.layout_main.addWidget(self.list_widget)
        
        btn_box = QHBoxLayout()
        self.btn_connect = QPushButton("Connect Device")
        self.btn_connect.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(self.btn_connect)
        self.layout_main.addLayout(btn_box)

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
        self.x_data = np.linspace(-self.buffer_size/self.fs, 0, self.buffer_size)
        
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

        self.data1 = np.zeros(self.buffer_size)
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
            
            self.data2 = np.zeros(self.buffer_size)
            # HR is Red
            c2 = COLOR_HR if "Heart" in right_label else COLOR_RECORD
            
            self.curve2 = pg.PlotCurveItem(self.x_data, self.data2, pen=pg.mkPen(c2, width=2, style=Qt.DashLine), name=right_label)
            self.vb2.addItem(self.curve2)
            
            # Add to legend manually since it's on a different viewbox
            self.legend.addItem(self.curve2, right_label)
            
            self.plot_item.vb.sigResized.connect(self.update_views)
        else:
            # Same axis (Bottom Graph: Phasic vs Tonic)
            self.data2 = np.zeros(self.buffer_size)
            # Tonic is Gold
            c2 = COLOR_TONIC
            self.curve2 = self.plot_widget.plot(self.x_data, self.data2, pen=pg.mkPen(c2, width=2), name="Tonic Level")

    def update_views(self):
        if self.dual_axis:
            self.vb2.setGeometry(self.plot_item.vb.sceneBoundingRect())
            self.vb2.linkedViewChanged(self.plot_item.vb, self.vb2.XAxis)

    def reset_data(self):
        self.x_data = np.linspace(-self.buffer_size/self.fs, 0, self.buffer_size)
        self.data1 = np.zeros(self.buffer_size)
        self.data2 = np.zeros(self.buffer_size)
        self.curve1.setData(self.x_data, self.data1)
        self.curve2.setData(self.x_data, self.data2)
        # Clear lines
        for item in self.plot_widget.items():
            if isinstance(item, pg.InfiniteLine):
                self.plot_widget.removeItem(item)

    def add_marker(self, text, color_hex):
        """Adds a marker at the current latest timestamp (right side)"""
        current_time = self.x_data[-1]
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

    def update_step(self, recording=False):
        if not recording: return

        # Shift Time Window
        dt = 1.0 / self.fs
        new_time = self.x_data[-1] + dt
        
        # Shift X Data
        self.x_data[:-1] = self.x_data[1:]
        self.x_data[-1] = new_time
        
        # Shift Y Data
        self.data1[:-1] = self.data1[1:]
        self.data2[:-1] = self.data2[1:]
        
        # Generate new values based on time
        t = new_time
        
        if self.dual_axis:
            # EDA (Blue) - Slow
            new_val1 = 5.0 + np.sin(t/5) + np.random.normal(0, 0.05)
            # HR (Red) - Faster, Higher magnitude
            new_val2 = 75.0 + np.sin(t/2)*10 + np.random.normal(0, 1.0)
        else:
            # Phasic (Blue) - Zero centered, spiky
            new_val1 = np.random.normal(0, 0.2) * (1.0 if np.random.random() > 0.8 else 0.0)
            # Tonic (Gold) - Slow drift
            new_val2 = 5.0 + np.sin(t/10)*2
            
        self.data1[-1] = new_val1
        self.data2[-1] = new_val2
        
        # Update Curves with new coordinate systems
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
        self.is_recording = False
        self.active_flags = [] # Stores dicts of {timestamp, line_obj, list_item}
        
        QApplication.instance().setStyleSheet(ResearchStyleSheet.get_stylesheet())
        self.setup_ui()
        
        # Simulation Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_loop)

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
            ("Hardware\nDiagnostics", QStyle.SP_DriveHDIcon, lambda: QMessageBox.information(self, "Diagnostics", "Running Hardware Diagnostics..."))
        ])
        self.ribbon_tabs.addTab(setup_page, "Setup")

        # GROUP 2: RECORDING
        # Using built-in icons to approximate Gear/Waveform
        acq_page = create_page([
            ("Hardware\nConfig", QStyle.SP_FileDialogDetailedView, None), # Gear-ish
            ("Noise\nThresholds", QStyle.SP_DriveNetIcon, None), # Waveform-ish
            ("Activity\nProfile", QStyle.SP_MediaSeekForward, None) # Motion-ish
        ])
        self.ribbon_tabs.addTab(acq_page, "Recording")
        
        # GROUP 3: ANALYSIS
        ana_page = create_page([
            ("Run\ncvxEDA", QStyle.SP_MediaPlay, lambda: QMessageBox.information(self, "Info", "Optimization Started")),
            ("Filter\nConfig", QStyle.SP_FileDialogListView, None),
            ("HRV\nDashboard", QStyle.SP_FileDialogContentsView, lambda: QMessageBox.information(self, "HRV", "Opening HRV Dashboard..."))
        ])
        self.ribbon_tabs.addTab(ana_page, "Analysis")
        
        # GROUP 4: EXPORT
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

        gl.addWidget(QLabel("Height: "), 3, 0)
        self.txt_sub_height = QLineEdit()
        self.txt_sub_height.setReadOnly(True)
        gl.addWidget(self.txt_sub_height, 3, 1)

        gl.addWidget(QLabel("Notes:"), 4, 0)
        self.txt_sub_notes = QTextEdit()
        self.txt_sub_notes.setReadOnly(True)
        self.txt_sub_notes.setMaximumHeight(50)
        gl.addWidget(self.txt_sub_notes, 4, 1)

        gl.addWidget(QLabel("Session:"), 5, 0)
        self.txt_session = QLineEdit("001")
        gl.addWidget(self.txt_session, 5, 1)
        
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
        
        hl.addLayout(v_eda)
        hl.addLayout(v_hr)
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

    # --- LOGIC ---
    def on_connect_request(self):
        dlg = ConnectDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.device_connected = True
            
            # Update UI
            self.lbl_conn.setText("CONNECTED")
            self.lbl_conn.setStyleSheet("color: green; border: 2px solid green; font-weight: bold; border-radius: 8px; background: #E8F5E9;")
            
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Start Live Session")
            self.btn_disconnect.setEnabled(True)
            
            self.statusBar().showMessage("Device Connected.")

    def on_disconnect(self):
        self.device_connected = False
        self.lbl_conn.setText("DISCONNECTED")
        self.lbl_conn.setStyleSheet("color: #777; border: 2px dashed #CCC; padding: 15px; border-radius: 8px;")
        
        self.btn_start.setEnabled(False)
        self.btn_start.setText("Start New Session")
        self.btn_disconnect.setEnabled(False)
        
        if self.timer.isActive():
            self.timer.stop()
            
        # Disable Recording Controls
        if self.btn_rec.isChecked():
            self.btn_rec.setChecked(False)
        self.btn_rec.setEnabled(False)
        self.btn_sim_start.setEnabled(False)
        self.btn_sim_pause.setEnabled(False)
        self.btn_sim_stop.setEnabled(False)
        self.statusBar().showMessage("Device Disconnected.")

    def on_start_session(self):
        if not self.device_connected: return
        
        # Enable Recording Controls
        self.btn_rec.setEnabled(True)
        self.btn_sim_start.setEnabled(True)
        self.btn_sim_pause.setEnabled(True)
        self.btn_sim_stop.setEnabled(True)
        
        # Switch View
        self.center_stack.setCurrentIndex(1)
        
        # Reset Graphs
        self.graph_main.reset_data()
        self.graph_sub.reset_data()
        
        self.statusBar().showMessage("Session Active. Press REC to start data stream.")
        self.on_start_sim()
        self.statusBar().showMessage("Session Active. Data stream started.")

    def on_load_clicked(self):
        QFileDialog.getOpenFileName(self, "Load Data", "", "CSV Files (*.csv)")

    def on_record_toggled(self, checked):
        self.is_recording = checked
        if checked:
            self.lbl_rec_hint.setText("RECORDING")
            self.lbl_rec_hint.setStyleSheet(f"color: {COLOR_RECORD}; font-weight: bold;")
        else:
            self.lbl_rec_hint.setText("Paused")
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
        ts = self.graph_main.x_data[-1]
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

    def game_loop(self):
        # Update Graphs
        self.graph_main.update_step(True)
        self.graph_sub.update_step(True)
        
        # Update Metrics
        val_eda = self.graph_main.data1[-1]
        val_hr = self.graph_main.data2[-1]
        
        self.val_eda.setText(f"{val_eda:.2f} µS")
        self.val_hr.setText(f"{int(val_hr)} BPM")

    def on_start_sim(self):
        self.timer.start(50)

    def on_pause_sim(self):
        self.timer.stop()

    def on_stop_sim(self):
        was_running = self.timer.isActive()
        self.timer.stop()
        
        dlg = ExitDialog(self, "Stop Session?", "Stop Recording", "Do you want to save the recorded data?")
        if dlg.exec() == QDialog.Accepted:
            if dlg.action == 'save':
                print("Saving Session Data...")
            elif dlg.action == 'discard':
                print("Session Stopped")
        elif was_running:
            self.timer.start()

    def closeEvent(self, event):
        dlg = ExitDialog(self)
        if dlg.exec() == QDialog.Accepted:
            if dlg.action == 'save':
                print("Saving...")
                event.accept()
            elif dlg.action == 'discard':
                print("Discarding...")
                event.accept()
        else:
            event.ignore()
    def open_subject_data_dialog(self):
        dialog = SubjectDataDialog(self)
        if dialog.exec():
            # If data was saved, populate the left panel
            if dialog.saved_data:
                if len(dialog.saved_data) == 5:
                    sid, name, sex, height, notes = dialog.saved_data
                    self.txt_sub_id.setText(str(sid))
                else:
                    name, sex, height, notes = dialog.saved_data
                    self.txt_sub_id.setText("New")

                self.txt_sub_name.setText(name)
                self.txt_sub_sex.setText(sex)
                self.txt_sub_height.setText(str(height))
                self.txt_sub_notes.setText(notes)
            self.statusBar().showMessage("Subject metadata updated successfully.", 5000)

    def on_import_subject(self):
        dlg = SubjectSelectionDialog(self)
        if dlg.exec():
            sub = dlg.selected_subject
            if sub:
                # sub is tuple: (id, name, sex, height, notes)
                self.txt_sub_id.setText(str(sub[0]))
                self.txt_sub_name.setText(sub[1])
                self.txt_sub_sex.setText(sub[2])
                self.txt_sub_height.setText(str(sub[3]))
                self.txt_sub_notes.setText(sub[4])
                self.statusBar().showMessage(f"Imported subject: {sub[1]}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())