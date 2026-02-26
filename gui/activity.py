from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QListWidget, 
                               QPushButton, QGroupBox, QFormLayout, QLineEdit, 
                               QDoubleSpinBox, QComboBox, QLabel, QMessageBox, 
                               QWidget)
from PySide6.QtCore import Qt
from colorConstraints import *

# Mock Backend Data
PROFILES = {
    "Stationary": {
        "is_default": True,
        "eda_threshold": 0.01,
        "hr_filter_hz": 2.0,
        "artifact_aggressiveness": "Low"
    },
    "Moving": {
        "is_default": True,
        "eda_threshold": 0.05,
        "hr_filter_hz": 5.0,
        "artifact_aggressiveness": "High"
    }
}

class ActivityProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activity Profiles")
        self.setMinimumSize(600, 400)
        self.setStyleSheet(ResearchStyleSheet.get_stylesheet())
        
        self.current_profile_key = None
        
        self.setup_ui()
        self.populate_list()
        
        # Select the first item by default
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Left Panel: Profile List ---
        left_panel = QVBoxLayout()
        
        lbl_list = QLabel("Available Profiles")
        lbl_list.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold;")
        left_panel.addWidget(lbl_list)
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        left_panel.addWidget(self.list_widget)
        
        btn_box = QHBoxLayout()
        self.btn_add = QPushButton("Add Custom")
        self.btn_add.setObjectName("secondary")
        self.btn_add.clicked.connect(self.on_add_custom)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("secondary")
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_delete.setEnabled(False)
        
        btn_box.addWidget(self.btn_add)
        btn_box.addWidget(self.btn_delete)
        left_panel.addLayout(btn_box)
        
        main_layout.addLayout(left_panel, 1) # Stretch factor 1
        
        # --- Right Panel: Detail View ---
        right_panel = QVBoxLayout()
        
        self.grp_box = QGroupBox("Profile Tolerances")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Fields
        self.txt_name = QLineEdit()
        self.txt_name.textChanged.connect(self.update_active_profile_data)
        
        self.spin_eda = QDoubleSpinBox()
        self.spin_eda.setRange(0.0, 10.0)
        self.spin_eda.setSingleStep(0.01)
        self.spin_eda.setSuffix(" µS")
        self.spin_eda.valueChanged.connect(self.update_active_profile_data)
        
        self.spin_hr = QDoubleSpinBox()
        self.spin_hr.setRange(0.0, 20.0)
        self.spin_hr.setSingleStep(0.5)
        self.spin_hr.setSuffix(" Hz")
        self.spin_hr.valueChanged.connect(self.update_active_profile_data)
        
        self.combo_aggressiveness = QComboBox()
        self.combo_aggressiveness.addItems(["Low", "Medium", "High"])
        self.combo_aggressiveness.currentTextChanged.connect(self.update_active_profile_data)
        
        form_layout.addRow("Profile Name:", self.txt_name)
        form_layout.addRow("EDA Phasic Threshold:", self.spin_eda)
        form_layout.addRow("HR Low-Pass Cutoff:", self.spin_hr)
        form_layout.addRow("Artifact Aggressiveness:", self.combo_aggressiveness)
        
        self.grp_box.setLayout(form_layout)
        right_panel.addWidget(self.grp_box)
        
        right_panel.addStretch()
        
        self.btn_apply = QPushButton("Apply Selected Profile")
        self.btn_apply.setFixedSize(250, 50)
        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_PRIMARY};
                color: {COLOR_BG_WHITE};
                font-weight: bold;
                font-size: 11pt;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #0A3D70;
            }}
        """)
        self.btn_apply.clicked.connect(self.on_apply)
        
        # Center the button
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(self.btn_apply)
        btn_container.addStretch()
        right_panel.addLayout(btn_container)
        
        main_layout.addLayout(right_panel, 2) # Stretch factor 2

    def populate_list(self):
        self.list_widget.clear()
        for name in PROFILES:
            self.list_widget.addItem(name)

    def on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.grp_box.setEnabled(False)
            self.btn_delete.setEnabled(False)
            return
            
        name = items[0].text()
        self.current_profile_key = name
        data = PROFILES[name]
        is_default = data.get("is_default", False)
        
        # Block signals to prevent auto-update during population
        self.block_signals_fields(True)
        
        self.txt_name.setText(name)
        self.spin_eda.setValue(data["eda_threshold"])
        self.spin_hr.setValue(data["hr_filter_hz"])
        self.combo_aggressiveness.setCurrentText(data["artifact_aggressiveness"])
        
        self.block_signals_fields(False)
        
        # UI Logic based on default status
        if is_default:
            self.btn_delete.setEnabled(False)
            self.txt_name.setReadOnly(True)
            self.spin_eda.setEnabled(False)
            self.spin_hr.setEnabled(False)
            self.combo_aggressiveness.setEnabled(False)
        else:
            self.btn_delete.setEnabled(True)
            self.txt_name.setReadOnly(False)
            self.spin_eda.setEnabled(True)
            self.spin_hr.setEnabled(True)
            self.combo_aggressiveness.setEnabled(True)
            
        self.grp_box.setEnabled(True)

    def block_signals_fields(self, block):
        self.txt_name.blockSignals(block)
        self.spin_eda.blockSignals(block)
        self.spin_hr.blockSignals(block)
        self.combo_aggressiveness.blockSignals(block)

    def update_active_profile_data(self):
        if not self.current_profile_key: return
        
        # Don't update if it's a default profile (double check)
        if PROFILES[self.current_profile_key].get("is_default", False):
            return

        new_name = self.txt_name.text()
        
        # Update values
        PROFILES[self.current_profile_key]["eda_threshold"] = self.spin_eda.value()
        PROFILES[self.current_profile_key]["hr_filter_hz"] = self.spin_hr.value()
        PROFILES[self.current_profile_key]["artifact_aggressiveness"] = self.combo_aggressiveness.currentText()
        
        # Handle Renaming if name changed and is valid
        if new_name and new_name != self.current_profile_key:
            if new_name not in PROFILES:
                data = PROFILES.pop(self.current_profile_key)
                PROFILES[new_name] = data
                self.current_profile_key = new_name
                
                # Update List Item Text without triggering selection change full reload
                item = self.list_widget.selectedItems()[0]
                item.setText(new_name)

    def on_add_custom(self):
        base_name = "Custom Profile"
        count = 1
        while f"{base_name} {count}" in PROFILES:
            count += 1
        
        new_name = f"{base_name} {count}"
        
        # Default custom values
        PROFILES[new_name] = {
            "is_default": False,
            "eda_threshold": 0.02,
            "hr_filter_hz": 3.0,
            "artifact_aggressiveness": "Medium"
        }
        
        self.list_widget.addItem(new_name)
        # Select the new item
        items = self.list_widget.findItems(new_name, Qt.MatchExactly)
        if items:
            self.list_widget.setCurrentItem(items[0])

    def on_delete(self):
        if not self.current_profile_key: return
        
        if PROFILES[self.current_profile_key].get("is_default", False):
            return # Should be disabled anyway
            
        del PROFILES[self.current_profile_key]
        
        # Remove from list
        row = self.list_widget.currentRow()
        self.list_widget.takeItem(row)
        self.current_profile_key = None

    def on_apply(self):
        if self.current_profile_key:
            print(f"Profile '{self.current_profile_key}' Applied")
            self.accept()
