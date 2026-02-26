from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFrame, QStyle)
from PySide6.QtCore import Qt, QSize
from colorConstraints import *

# Mocking extracted error codes based on typical firmware definitions
# 0xE1 is a common error for WHO_AM_I register mismatch in IMUs like BMI270/MPU6050
ERROR_CODES = {
    0x00: "OK",
    0x01: "I2C_BUS_TIMEOUT",
    0x02: "SENSOR_NOT_FOUND",
    0xE1: "GYRO_INIT_FAILED: WHO_AM_I mismatch",
    0xE2: "GSR_ADC_OVERFLOW",
    0xE3: "HR_SIGNAL_NOISY"
}

# Fallback for success green if not in colorConstraints
SUCCESS_GREEN = "#5cb85c"

class HardwareDiagnosticsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hardware Diagnostics")
        self.setFixedSize(500, 380)
        
        # Apply project global styles
        self.setStyleSheet(ResearchStyleSheet.get_stylesheet())
        
        layout = QVBoxLayout(self)
        
        # --- Header ---
        header = QLabel("Sensor Health Check")
        header.setObjectName("h1") # Uses the h1 style from ResearchStyleSheet
        layout.addWidget(header)
        
        # --- Checklist Container ---
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_WHITE}; 
                border-radius: 8px; 
                border: 1px solid #CCC;
            }}
        """)
        list_layout = QVBoxLayout(container)
        list_layout.setSpacing(15)
        list_layout.setContentsMargins(20, 20, 20, 20)
        
        # Mock Diagnostic State
        # Format: (Sensor Name, Error Code)
        sensors = [
            ("MAX86141 Pulse Sensor", 0x00), # SUCCESS
            ("GSR Skin Conductance", 0x00),  # SUCCESS
            ("BMI270 Gyroscope", 0xE1)       # FAILURE (Mocked from gyrscope_code.c)
        ]
        
        for name, code in sensors:
            row = QHBoxLayout()
            
            # 1. Icon
            icon_lbl = QLabel()
            if code == 0x00:
                icon = self.style().standardIcon(QStyle.SP_DialogApplyButton)
                status_text = "Online"
                status_color = SUCCESS_GREEN
            else:
                icon = self.style().standardIcon(QStyle.SP_DialogCancelButton)
                status_text = ERROR_CODES.get(code, f"Unknown Error (0x{code:02X})")
                status_color = COLOR_RECORD # Red from constraints
            
            icon_lbl.setPixmap(icon.pixmap(QSize(24, 24)))
            row.addWidget(icon_lbl)
            
            # 2. Sensor Name
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"font-weight: bold; font-size: 11pt; color: {COLOR_TEXT}; border: none;")
            row.addWidget(name_lbl, 1) # Stretch factor 1 to push status to right
            
            # 3. Status Text
            status_lbl = QLabel(status_text)
            status_lbl.setStyleSheet(f"color: {status_color}; font-weight: 600; border: none;")
            status_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(status_lbl)
            
            list_layout.addLayout(row)
            
            # Divider line (optional, for aesthetics)
            if sensors.index((name, code)) < len(sensors) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setFrameShadow(QFrame.Sunken)
                line.setStyleSheet("background-color: #EEE; border: none; max-height: 1px;")
                list_layout.addWidget(line)

        layout.addWidget(container)
        layout.addStretch()
        
        # --- Footer ---
        btn_close = QPushButton("Close")
        btn_close.setObjectName("secondary")
        btn_close.setFixedSize(100, 40)
        btn_close.clicked.connect(self.accept)
        
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(btn_close)
        layout.addLayout(footer)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    dlg = HardwareDiagnosticsDialog()
    dlg.show()
    sys.exit(app.exec())
