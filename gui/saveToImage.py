import os
import numpy as np
import neurokit2 as nk
import matplotlib.pyplot as plt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QCheckBox, 
                               QFileDialog, QMessageBox)
from PySide6.QtCore import Qt

# --- IMAGE EXPORT MANAGER ---
class ImageExportManager:
    """
    Handles the underlying file writing logic for exporting session plots to images.
    """
    def __init__(self):
        pass

    def export_images(self, data: dict, filepath: str, split_files: bool = False) -> tuple[bool, str]:
        """
        Exports selected data dict to a PNG image using matplotlib.
        """
        try:
            time_data = data.get("Time")
            if time_data is None or len(time_data) == 0:
                return False, "No time data available."
            
            # Filter out Time and EVENTS from the signals to plot
            signals = {k: v for k, v in data.items() if k not in ["Time", "EVENTS"] and len(v) > 0}
            
            # Extract sampling rate from time array
            time_arr = np.array(time_data)
            fs = 20 # sensible default
            if len(time_arr) > 1:
                diffs = np.diff(time_arr)
                diffs = diffs[diffs > 0]
                if len(diffs) > 0:
                    calculated_fs = 1.0 / np.mean(diffs)
                    if np.isfinite(calculated_fs) and calculated_fs > 0:
                        fs = int(np.round(calculated_fs))
            
            # Pre-compute physiological markers using neurokit2 pipelines
            eda_info = None
            if "EDA_Raw" in signals:
                try: _, eda_info = nk.eda_process(signals["EDA_Raw"], sampling_rate=fs)
                except Exception: pass
            elif "EDA_Smooth" in signals:
                try: _, eda_info = nk.eda_process(signals["EDA_Smooth"], sampling_rate=fs)
                except Exception: pass
                    
            ppg_info = None
            if "PPG_Raw" in signals:
                try: _, ppg_info = nk.ppg_process(signals["PPG_Raw"], sampling_rate=fs)
                except Exception: pass

            ecg_info = None
            if "ECG_Raw" in signals:
                try: _, ecg_info = nk.ecg_process(signals["ECG_Raw"], sampling_rate=fs)
                except Exception: pass

            def add_nk_markers(ax, sig_name, sig_arr):
                """Helper function to cleanly overlay extracted markers onto a matplotlib axis."""
                if "EDA" in sig_name and "Tonic" not in sig_name and eda_info:
                    onsets = [int(x) for x in eda_info.get("SCR_Onsets", []) if not np.isnan(x) and 0 <= x < len(time_arr)]
                    peaks = [int(x) for x in eda_info.get("SCR_Peaks", []) if not np.isnan(x) and 0 <= x < len(time_arr)]
                    recoveries = [int(x) for x in eda_info.get("SCR_Recovery", []) if not np.isnan(x) and 0 <= x < len(time_arr)]
                    
                    if onsets: ax.scatter(time_arr[onsets], sig_arr[onsets], color='#D9534F', marker='v', zorder=5, label='SCR Onset')
                    if peaks: ax.scatter(time_arr[peaks], sig_arr[peaks], color='#FFC600', marker='o', zorder=5, label='SCR Peak')
                    if recoveries: ax.scatter(time_arr[recoveries], sig_arr[recoveries], color='#5cb85c', marker='s', zorder=5, label='SCR Recovery')
                        
                if "PPG" in sig_name and ppg_info:
                    peaks = [int(x) for x in ppg_info.get("PPG_Peaks", []) if not np.isnan(x) and 0 <= x < len(time_arr)]
                    if peaks: ax.scatter(time_arr[peaks], sig_arr[peaks], color='#D9534F', marker='o', zorder=5, label='PPG Peak')
                        
                if "ECG" in sig_name and ecg_info:
                    peaks = [int(x) for x in ecg_info.get("ECG_R_Peaks", []) if not np.isnan(x) and 0 <= x < len(time_arr)]
                    if peaks: ax.scatter(time_arr[peaks], sig_arr[peaks], color='#D9534F', marker='o', zorder=5, label='R-Peak')

            # Set default styling
            plt.style.use('default')
            
            if split_files:
                base_name, ext = os.path.splitext(filepath)
                if not ext: ext = ".png"
                for sig_name, sig_data in signals.items():
                    fig, ax = plt.subplots(figsize=(10, 4))
                    sig_arr = np.array(sig_data)
                    ax.plot(time_data, sig_data, label=sig_name, color='#07294D') # Drexel Blue
                    add_nk_markers(ax, sig_name, sig_arr)
                    ax.set_title(f"{sig_name} over Time", fontweight='bold')
                    ax.set_xlabel("Time (s)")
                    ax.set_ylabel(sig_name)
                    ax.grid(True, linestyle='--', alpha=0.7)
                    ax.legend(loc='upper right')
                    fig.tight_layout()
                    
                    col_filepath = f"{base_name}_{sig_name}{ext}"
                    fig.savefig(col_filepath, dpi=300)
                    plt.close(fig)
            else:
                num_signals = len(signals)
                if num_signals == 0:
                    return False, "No signals to plot."
                
                fig, axes = plt.subplots(num_signals, 1, figsize=(10, 2.5 * num_signals), sharex=True)
                if num_signals == 1:
                    axes = [axes]
                
                # NeuroKit2 style multi-color palette
                colors = ['#07294D', '#D9534F', '#FFC600', '#5bc0de', '#5cb85c']
                
                for i, (ax, (sig_name, sig_data)) in enumerate(zip(axes, signals.items())):
                    c = colors[i % len(colors)]
                    sig_arr = np.array(sig_data)
                    ax.plot(time_data, sig_data, label=sig_name, color=c)
                    add_nk_markers(ax, sig_name, sig_arr)
                    ax.set_ylabel(sig_name)
                    ax.grid(True, linestyle='--', alpha=0.7)
                    ax.legend(loc="upper right")
                
                axes[-1].set_xlabel("Time (s)")
                fig.suptitle("Session Data Overview", fontsize=14, fontweight='bold')
                fig.tight_layout()
                fig.savefig(filepath, dpi=300)
                plt.close(fig)
                
            return True, "Images saved successfully."
        except Exception as e:
            return False, str(e)


# --- UI DIALOG ---
class ImageExportDialog(QDialog):
    """
    User interface for saving graph images.
    """
    def __init__(self, data=None, default_filename="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Graph Image")
        self.setFixedSize(450, 220)
        
        self.data = data if data is not None else {}
        self.default_filename = default_filename
        self.manager = ImageExportManager()
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        header = QLabel("Save Graph Image")
        header.setObjectName("h1")
        main_layout.addWidget(header)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

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

        self.cb_split = QCheckBox("Save each signal as a separate image file")
        form_layout.addRow(self.cb_split)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.validate_and_save)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        main_layout.addLayout(btn_layout)

    def browse_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Image File", self.default_filename, "PNG Files (*.png);;All Files (*)")
        if path:
            self.input_path.setText(path)

    def validate_and_save(self):
        filepath = self.input_path.text().strip()
        
        if not filepath:
            QMessageBox.warning(self, "Validation Error", "Please select a destination file path.")
            return
            
        if not self.data or len(self.data) == 0:
            QMessageBox.information(self, "No Data", "There is no session data available to save.")
            return

        split_files = self.cb_split.isChecked()
        success, message = self.manager.export_images(self.data, filepath, split_files)
        
        if success:
            msg = "Images successfully saved to separate files." if split_files else f"Image successfully saved to:\n{filepath}"
            QMessageBox.information(self, "Export Complete", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Export Failed", f"An error occurred during export:\n{message}")