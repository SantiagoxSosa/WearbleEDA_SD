import sys
import datetime
import random
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                               QGroupBox, QFrame, QStatusBar, QMenuBar, QMenu, 
                               QDialog, QListWidget, QStackedWidget, QMessageBox,
                               QGridLayout, QTabWidget, QToolButton, QFileDialog,
                               QSizePolicy, QSplitter, QAbstractItemView)
from PySide6.QtCore import Qt, QTimer, QSize, QTime
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QPalette

import pyqtgraph as pg

# --- DESIGN SYSTEM CONSTANTS (DREXEL UNIVERSITY) ---
COLOR_PRIMARY = "#07294D"   # Drexel Blue
COLOR_ACCENT  = "#FFC600"   # Drexel Gold
COLOR_BG_LIGHT= "#F5F5F5"   # Light Gray
COLOR_BG_WHITE= "#FFFFFF"   # Pure White
COLOR_TEXT    = "#333333"   # Dark Gray / Black
COLOR_RECORD  = "#D9534F"   # Red for recording state
COLOR_EDA     = "#07294D"   # Primary Blue for EDA/Phasic
COLOR_HR      = "#D9534F"   # Red for Heart Rate
COLOR_TONIC   = "#FFC600"   # Gold for Tonic

FONT_UI       = "Segoe UI"
FONT_MONO     = "Consolas"

class ResearchStyleSheet:
    @staticmethod
    def get_stylesheet():
        return f"""
        QMainWindow {{ background-color: {COLOR_BG_LIGHT}; }}
        QWidget {{ font-family: "{FONT_UI}"; font-size: 10pt; color: {COLOR_TEXT}; }}
        
        /* HEADER & MENU */
        QMenuBar {{ 
            background-color: {COLOR_PRIMARY}; 
            color: white; 
            border-bottom: 2px solid {COLOR_ACCENT}; 
        }}
        QMenuBar::item {{ background: transparent; color: white; padding: 8px 15px; }}
        QMenuBar::item:selected {{ background: #0A3D70; }}
        
        /* RIBBON */
        QTabWidget::pane {{ border: 1px solid #DDDDDD; background: {COLOR_BG_WHITE}; border-radius: 8px; }}
        QTabBar::tab {{
            background: {COLOR_BG_LIGHT};
            border: 1px solid #DDDDDD;
            padding: 8px 20px;
            margin-right: 4px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }}
        QTabBar::tab:selected {{
            background: {COLOR_BG_WHITE};
            border-bottom-color: {COLOR_BG_WHITE};
            font-weight: bold;
            color: {COLOR_PRIMARY};
            border-top: 3px solid {COLOR_ACCENT};
        }}
        
        /* BUTTONS */
        QPushButton {{ 
            background-color: {COLOR_PRIMARY}; 
            color: white; 
            border-radius: 8px; 
            padding: 8px; 
            border: none;
            font-weight: bold;
        }}
        QPushButton:disabled {{ background-color: #CCCCCC; color: #888888; }}
        QPushButton:hover {{ background-color: #0A3D70; }}
        
        /* Secondary Button Style */
        QPushButton#secondary {{ 
            background-color: #E0E0E0; 
            color: {COLOR_TEXT}; 
            border: 1px solid #CCC; 
        }}
        QPushButton#secondary:hover {{ background-color: #D0D0D0; }}

        /* Accent Button (Insert Event) */
        QPushButton#accent {{ 
            background-color: {COLOR_PRIMARY}; 
            color: {COLOR_ACCENT}; 
            border: 1px solid #E5B000;
        }}
        QPushButton#accent:hover {{ background-color: #FFD700; }}
        
        /* INPUTS */
        QLineEdit {{ 
            border: 1px solid #CCC; 
            border-radius: 8px; 
            padding: 5px; 
            background: white; 
            color: {COLOR_TEXT};
        }}
        
        /* GROUP BOXES */
        QGroupBox {{ 
            font-weight: bold; 
            border: 1px solid #CCC; 
            margin-top: 25px; 
            background: {COLOR_BG_WHITE}; 
            border-radius: 8px; 
        }}
        QGroupBox::title {{ 
            subcontrol-origin: margin; 
            subcontrol-position: top left; 
            padding: 0 5px; 
            color: {COLOR_PRIMARY}; 
        }}
        
        /* LISTS */
        QListWidget {{ 
            border: 1px solid #CCC; 
            background: {COLOR_BG_WHITE}; 
            border-radius: 8px; 
            outline: none;
        }}
        QListWidget::item:selected {{
            background: {COLOR_PRIMARY};
            color: white;
            border-radius: 4px;
        }}
        
        /* MODALS (Strict Light Mode) */
        QDialog {{ background-color: {COLOR_BG_WHITE}; }}
        QLabel#h1 {{ color: {COLOR_PRIMARY}; font-size: 14pt; font-weight: bold; }}
        
        QFrame#event_bar {{
            background: {COLOR_BG_LIGHT};
            border: 1px solid #CCC;
            border-radius: 8px;
        }}
        """

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
            "EDA_DEVICE_A1 (RSSI: -45dBm | Bat: 98%)", 
            "EDA_DEVICE_B2 (RSSI: -72dBm | Bat: 45%)"
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
    def __init__(self, parent=None):
        super().__init__("Save Session?", parent)
        self.setFixedSize(400, 180)
        
        header = QLabel("End Session")
        header.setObjectName("h1")
        self.layout_main.addWidget(header)
        
        self.layout_main.addWidget(QLabel("Do you want to save the session before exiting?"))
        
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
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Configuration
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=True)

        self.plot_widget = pg.PlotWidget(title=title)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush(255,255,255,200)) # Semi-transparent white
        self.plot_widget.setLabel('bottom', "Time", units='s')
        self.plot_widget.setLabel('left', left_label, units=left_unit)
        
        self.layout.addWidget(self.plot_widget)
        
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
        
        # Scroll the view to keep the right edge at new_time
        # Show roughly 10-15 seconds history
        self.plot_widget.setXRange(new_time - 15, new_time)

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
        self.timer.start(50) # 20Hz update

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
            ("Connect\nDevice", pg.QtWidgets.QStyle.SP_ComputerIcon, self.on_connect_request),
            ("Subject\nData", pg.QtWidgets.QStyle.SP_FileDialogInfoView, None)
        ])
        self.ribbon_tabs.addTab(setup_page, "Setup")

        # GROUP 2: RECORDING
        # Using built-in icons to approximate Gear/Waveform
        acq_page = create_page([
            ("Recording\nSettings", pg.QtWidgets.QStyle.SP_FileDialogDetailedView, None), # Gear-ish
            ("Tolerances", pg.QtWidgets.QStyle.SP_DriveNetIcon, None) # Waveform-ish
        ])
        self.ribbon_tabs.addTab(acq_page, "Recording")
        
        # GROUP 3: ANALYSIS
        ana_page = create_page([
            ("Run\ncvxEDA", pg.QtWidgets.QStyle.SP_MediaPlay, lambda: QMessageBox.information(self, "Info", "Optimization Started")),
            ("Filter\nConfig", pg.QtWidgets.QStyle.SP_FileDialogListView, None)
        ])
        self.ribbon_tabs.addTab(ana_page, "Analysis")
        
        # GROUP 4: EXPORT
        exp_page = create_page([
            ("Export\nCSV", pg.QtWidgets.QStyle.SP_FileIcon, lambda: print("Exporting CSV...")),
            ("Save Graph\nImage", pg.QtWidgets.QStyle.SP_DialogSaveButton, lambda: print("Saving Image..."))
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
        gl.addWidget(QLabel("Subject ID:"), 0,0)
        gl.addWidget(QLineEdit("SUB-042"), 0,1)
        gl.addWidget(QLabel("Session:"), 1,0)
        gl.addWidget(QLineEdit("001"), 1,1)
        grp_sub.setLayout(gl)
        layout.addWidget(grp_sub)
        
        # Device Status
        grp_dev = QGroupBox("Device Status")
        dl = QVBoxLayout()
        self.lbl_conn = QLabel("DISCONNECTED")
        self.lbl_conn.setAlignment(Qt.AlignCenter)
        self.lbl_conn.setStyleSheet("color: #777; border: 2px dashed #CCC; padding: 15px; border-radius: 8px;")
        dl.addWidget(self.lbl_conn)
        
        t_grid = QGridLayout()
        t_grid.addWidget(QLabel("Battery:"), 0, 0)
        self.lbl_batt = QLabel("-- %")
        t_grid.addWidget(self.lbl_batt, 0, 1)
        t_grid.addWidget(QLabel("Signal:"), 1, 0)
        self.lbl_sig = QLabel("-- dBm")
        t_grid.addWidget(self.lbl_sig, 1, 1)
        dl.addLayout(t_grid)
        grp_dev.setLayout(dl)
        layout.addWidget(grp_dev)
        
        # Recording Button
        grp_rec = QGroupBox("Recording Control")
        rl = QVBoxLayout()
        self.btn_rec = QPushButton("REC")
        self.btn_rec.setCheckable(True)
        self.btn_rec.setFixedSize(100, 100)
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
        title.setFont(QFont(FONT_UI, 32, QFont.Bold))
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
        vl = QVBoxLayout()
        
        self.val_eda = QLabel("-- µS")
        self.val_eda.setFont(QFont(FONT_MONO, 24, QFont.Bold))
        self.val_eda.setStyleSheet(f"color: {COLOR_EDA}")
        
        self.val_hr = QLabel("-- BPM")
        self.val_hr.setFont(QFont(FONT_MONO, 24, QFont.Bold))
        self.val_hr.setStyleSheet(f"color: {COLOR_HR}")
        
        vl.addWidget(QLabel("Skin Conductance:"))
        vl.addWidget(self.val_eda)
        vl.addSpacing(20)
        vl.addWidget(QLabel("Heart Rate:"))
        vl.addWidget(self.val_hr)
        grp_met.setLayout(vl)
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

    def create_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("System Ready - Connect Device to Begin")

    # --- LOGIC ---
    def on_connect_request(self):
        dlg = ConnectDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.device_connected = True
            
            # Update UI
            self.lbl_conn.setText("CONNECTED")
            self.lbl_conn.setStyleSheet("color: green; border: 2px solid green; font-weight: bold; border-radius: 8px; background: #E8F5E9;")
            self.lbl_batt.setText("98%")
            self.lbl_sig.setText("-45 dBm")
            
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Start Live Session")
            self.statusBar().showMessage("Device Connected.")

    def on_start_session(self):
        if not self.device_connected: return
        
        # Switch View
        self.center_stack.setCurrentIndex(1)
        
        # Reset Graphs
        self.graph_main.reset_data()
        self.graph_sub.reset_data()
        
        self.statusBar().showMessage("Session Active. Press REC to start data stream.")

    def on_load_clicked(self):
        QFileDialog.getOpenFileName(self, "Load Data", "", "CSV Files (*.csv)")

    def on_record_toggled(self, checked):
        if not self.device_connected: 
            self.btn_rec.setChecked(False)
            return
            
        self.is_recording = checked
        if checked:
            self.lbl_rec_hint.setText("RECORDING")
            self.lbl_rec_hint.setStyleSheet(f"color: {COLOR_RECORD}; font-weight: bold;")
            self.statusBar().showMessage("Acquiring Data...")
        else:
            self.lbl_rec_hint.setText("Paused")
            self.lbl_rec_hint.setStyleSheet("color: black;")
            self.statusBar().showMessage("Acquisition Paused.")

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

    def create_status_bar(self):

        status = QStatusBar()

        self.setStatusBar(status)

        

        # Permanent widgets

        self.lbl_disk = QLabel("Disk: 45GB Free")

        self.lbl_ram = QLabel("RAM: 12% Used")

        self.lbl_time = QLabel()

        

        status.addPermanentWidget(self.lbl_disk)

        status.addPermanentWidget(self.lbl_ram)

        status.addPermanentWidget(self.lbl_time)

        

        # Update time

        timer = QTimer(self)

        timer.timeout.connect(lambda: self.lbl_time.setText(f"System Time: {datetime.datetime.now().strftime('%H:%M:%S')}"))

        timer.start(1000)



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
        self.graph_main.update_step(self.is_recording)
        self.graph_sub.update_step(self.is_recording)
        
        # Update Metrics
        if self.device_connected and self.is_recording:
            val_eda = self.graph_main.data1[-1]
            val_hr = self.graph_main.data2[-1]
            
            self.val_eda.setText(f"{val_eda:.2f} µS")
            self.val_hr.setText(f"{int(val_hr)} BPM")

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())