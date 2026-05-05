import os
import pandas as pd
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QCheckBox, 
                               QFileDialog, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt

# --- DATA EXPORT MANAGER ---
class ExportManager:
    """
    Handles the underlying file writing logic and data transformation
    for exporting session data to a CSV file.
    """
    def __init__(self):
        pass

    def export_csv(self, data, filepath: str, selected_columns: list, split_files: bool = False) -> tuple[bool, str]:
        """
        Exports selected columns from a dictionary or DataFrame to a CSV.
        
        Args:
            data: Dictionary of lists or a pandas DataFrame containing session data.
            filepath: Destination path for the CSV file.
            selected_columns: List of strings matching the signal columns to export.
            split_files: If True, exports each signal into its own separate CSV file.
            
        Returns:
            tuple: (success_boolean, message_string)
        """
        try:
            # Convert standard python dictionary into a DataFrame (or just use it if already a DataFrame)
            df = pd.DataFrame(data)
            
            # Ensure 'Time' or 'Timestamp' is always the first column if it exists in the data
            time_col = None
            if "Time" in df.columns:
                time_col = "Time"
            elif "Timestamp" in df.columns:
                time_col = "Timestamp"
            
            if not split_files:
                cols_to_export = []
                if time_col:
                    cols_to_export.append(time_col)
                
                # Append user-selected columns that actually exist in the data
                for col in selected_columns:
                    if col in df.columns and col not in cols_to_export:
                        cols_to_export.append(col)
                        
                # Filter DataFrame to only include requested columns
                df_export = df[cols_to_export]
                
                # Write to CSV
                df_export.to_csv(filepath, index=False)
            else:
                base_name, ext = os.path.splitext(filepath)
                for col in selected_columns:
                    if col in df.columns and col != time_col:
                        cols_to_export = [time_col, col] if time_col else [col]
                        col_filepath = f"{base_name}_{col}{ext}"
                        df[cols_to_export].to_csv(col_filepath, index=False)
            return True, "Export successful."
            
        except Exception as e:
            return False, str(e)


# --- UI DIALOG ---
class ExportDialog(QDialog):
    """
    User interface for selecting export configurations and destination paths.
    """
    def __init__(self, data=None, default_filename="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Session Data")
        self.setFixedSize(450, 400)
        
        self.data = data if data is not None else {}
        self.default_filename = default_filename
        self.manager = ExportManager()
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Export Session Data")
        header.setObjectName("h1")
        main_layout.addWidget(header)

        # Form Layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Destination File Browse
        path_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setReadOnly(True)
        self.input_path.setPlaceholderText("Select destination...")
        
        btn_browse = QPushButton("Browse")
        btn_browse.setObjectName("secondary")
        btn_browse.clicked.connect(self.browse_file)
        
        path_layout.addWidget(self.input_path)
        path_layout.addWidget(btn_browse)
        
        form_layout.addRow("Destination:", path_layout)

        # Signal Selection Checkboxes
        self.group_box = QGroupBox("Select Signals to Export")
        self.checkbox_layout = QVBoxLayout()
        self.checkboxes = {}
        
        # Sensible signals mapped from EDA/HRV processors
        signals = ["EDA_Raw", "EDA_Smooth", "EDA_Phasic", "EDA_Tonic", "PPG_Raw", "HRV_RMSSD", "EVENTS"]
        
        for sig in signals:
            cb = QCheckBox(sig)
            cb.setChecked(True) # Default all to checked
            self.checkboxes[sig] = cb
            self.checkbox_layout.addWidget(cb)
            
        self.group_box.setLayout(self.checkbox_layout)
        form_layout.addRow(self.group_box)

        # Split Files Checkbox
        self.cb_split = QCheckBox("Export each signal to a separate file")
        form_layout.addRow(self.cb_split)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_export = QPushButton("Export")
        btn_export.setDefault(True) # primary action, inherits standard styling
        btn_export.clicked.connect(self.validate_and_export)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_export)
        
        main_layout.addLayout(btn_layout)

    def browse_file(self):
        """Opens a file dialog to select the destination CSV."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Export File", self.default_filename, "CSV Files (*.csv);;All Files (*)")
        if path:
            self.input_path.setText(path)

    def validate_and_export(self):
        """Validates user input and calls the ExportManager."""
        filepath = self.input_path.text().strip()
        
        if not filepath:
            QMessageBox.warning(self, "Validation Error", "Please select a destination file path.")
            return
            
        selected_columns = [sig for sig, cb in self.checkboxes.items() if cb.isChecked()]
        
        if not selected_columns:
            QMessageBox.warning(self, "Validation Error", "Please select at least one signal to export.")
            return
            
        if not self.data or len(self.data) == 0:
            QMessageBox.information(self, "No Data", "There is no session data available to export.")
            return

        # Process export
        split_files = self.cb_split.isChecked()
        success, message = self.manager.export_csv(self.data, filepath, selected_columns, split_files)
        
        if success:
            msg = "Data successfully exported to separate files." if split_files else f"Data successfully exported to:\n{filepath}"
            QMessageBox.information(self, "Export Complete", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", f"An error occurred during export:\n{message}")