import neurokit2 as nk
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                               QGroupBox, QFrame, QStatusBar, QMenuBar, QMenu, 
                               QDialog, QListWidget, QStackedWidget, QMessageBox,
                               QGridLayout, QTabWidget, QToolButton, QFileDialog, QTextEdit, QComboBox, QFormLayout, QDoubleSpinBox,
                               QSizePolicy, QSplitter, QAbstractItemView, QStyle, QCheckBox)
from PySide6.QtCore import Qt, QTimer, QSize, QTime, QObject, Signal, Slot
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QPalette

import pyqtgraph as pg

# Show window for R-R intervals
class RRIntervalWindow(QWidget):
    def __init__(self, rri_ms, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RR Interval Analysis")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)

        pw = pg.PlotWidget(title="RR Intervals (ms)")
        pw.setLabel("left", "RR Interval", units="ms")
        pw.setLabel("bottom", "Beat Index")
        pw.showGrid(x=True, y=True, alpha=0.3)
        pw.setBackground("w")
        pg.setConfigOptions(antialias=True)

        if len(rri_ms) > 1: 
            x = np.arange(len(rri_ms))
            pw.plot(x, rri_ms, pen=pg.mkPen(color="#007ACC", width=2), symbol="o", symbolSize=8, symbolBrush="#007ACC")
            mean_rri = float(np.mean(rri_ms))
            
            pw.addItem(pg.InfiniteLine(mean_rri, angle=0, pen=pg.mkPen(color="#FF5733", width=1, style=Qt.DashLine), label=f"Mean: {mean_rri:.1f} ms",
                                       labelOpts={"color": "#3498DB", "position": 0.95}))
        # If there are not enough RR intervals, show a message
        else: 
            pw.addItem(pg.TextItem("Not enough RR intervals to plot", color="#FF5733"))

        layout.addWidget(pw)

# Show window for Poincare plot
class PoincarePlotWindow(QWidget):
    def __init__(self, rri_ms, hrv_nonlinear=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Poincare Plot")
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout(self)

        pw = pg.PlotWidget(title="Poincare Plot")
        pw.setLabel("left", "RR(n+1) (ms)")
        pw.setLabel("bottom", "RR(n) (ms)")
        pw.showGrid(x=True, y=True, alpha=0.3)
        pw.setBackground("w")
        pg.setConfigOptions(antialias=True)

        if len(rri_ms) > 2: 
            rr_n = rri_ms[:-1]
            rr_n1 = rri_ms[1:]
            scatterPlot = pg.ScatterPlotItem(rr_n, rr_n1, size=7, pen=pg.mkPen(color="#007ACC", width=2), symbol="o", symbolSize=8, symbolBrush="#007ACC")
            
            pw.addItem(scatterPlot)

            # identity line
            min_val = float(min(rri_ms)) - 20
            max_val = float(max(rri_ms)) + 20
            pw.plot([min_val, max_val], [min_val, max_val], pen=pg.mkPen(color="#FF5733", width=1, style=Qt.DashLine))
            
        layout.addWidget(pw)

        if hrv_nonlinear is not None:
            try:
                raw_sd1 = hrv_nonlinear.get("HRV_SD1", float("nan"))
                raw_sd2 = hrv_nonlinear.get("HRV_SD2", float("nan"))
                sd1 = float(raw_sd1[0]) if hasattr(raw_sd1, '__getitem__') else float(raw_sd1)
                sd2 = float(raw_sd2[0]) if hasattr(raw_sd2, '__getitem__') else float(raw_sd2)
                info_text = f"SD1: {sd1:.1f} ms\nSD2: {sd2:.1f} ms"
            except Exception as e:
                info_text = f"Error retrieving nonlinear metrics: {str(e)}"

            info_label = QLabel(info_text)
            info_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_label)

#PSD window
class PSDWindow(QWidget):
    def __init__(self, freq, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Power Spectral Density")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)

        pw = pg.PlotWidget(title="Power Spectral Density")
        pw.setLabel("left", "Power")
        pw.setLabel("bottom", "Frequency (Hz)")
        pw.showGrid(x=True, y=True, alpha=0.3)
        pw.setBackground("w")
        pg.setConfigOptions(antialias=True)

        if freq:
            try: 
                bands  = ["VLF",     "LF",      "HF"     ]
                keys   = ["HRV_VLF", "HRV_LF",  "HRV_HF" ]
                colors = ["#AED6F1", "#A9DFBF",  "#F9E79F"]

                values = []
                for key in keys:
                    try: 
                        raw = freq.get(key, 0)
                        val = float(raw[0]) if hasattr(raw, '__getitem__') else float(raw)
                        values.append(val if np.isfinite(val) else 0.0)
                    except: 
                        values.append(0.0)

                bar = pg.BarGraphItem(x=list(range(len(bands))), height=values, width=0.6, brushes=[pg.mkBrush(c) for c in colors])
                
                pw.addItem(bar)
                pw.getAxis("bottom").setTicks([[(i, band) for i, band in enumerate(bands)]])

                lf_hf_ratio = values[1] / values[2] if values[2] > 0 else float('inf')
                info_label =QLabel(f"VLF: {values[0]:.1f} ms²     LF: {values[1]:.1f} ms^2     "
                               f"HF: {values[2]:.1f} ms²     LF/HF: {lf_hf_ratio:.2f}")
                info_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(pw)
                layout.addWidget(info_label)

            except Exception as e:
                pw.addItem(pg.TextItem(f"Error rendering PSD: {str(e)}", color="#FF5733"))
                layout.addWidget(pw)
                
        else:
            pw.addItem(pg.TextItem("No frequency data available", color="#FF5733"))
            layout.addWidget(pw)

# Processor for HRV
# Buffers data, and rund HRV computation when enough data is collected
class HRVProcessor(QObject):
    hrv_computed = Signal(dict)
    hrv_error = Signal(str)

    def __init__(self, sampling_rate=256, window_second=30, parent=None):
        super().__init__(parent)
        self.sampling_rate = sampling_rate # Data points per second
        self.window_second = window_second
        self.window_size = window_second * sampling_rate # Windo second determines time of data required to compute HRV, size gives the total number of samples needed
        self.buffer = []

        # For plot windows
        self._rri_ms = np.array([])
        self._hrv_nonlinear = None
        self._hrv_freq = None

    def process_packet(self, packet):
        """Ingests a single packet from the main stream."""
        if packet.cardiac:
            # Buffer IR data for raw calculation
            self.receive_data([packet.cardiac.ir_value])

    @Slot(list)
    def receive_data(self, data):
        self.buffer.extend(data)

        if len(self.buffer) >= self.window_size:
            self.compute_hrv()
            self.buffer = self.buffer[-self.window_size:]

    @Slot()
    # Resets the buffer
    def reset(self):
        self.buffer = []
        self._rri_ms = np.array([])
        self._hrv_nonlinear = None
        self._hrv_freq = None

    # Computes HRV
    def compute_hrv(self):
        # Get the most recent sample
        try:
            window = np.array(self.buffer[-self.window_size:])

            # Process signals
            ppg_processed = nk.ppg_clean(window, sampling_rate=self.sampling_rate)
            # Extract peaks
            peaks = nk.ppg_findpeaks(ppg_processed, sampling_rate=self.sampling_rate)
            peak_loss = peaks["PPG_Peaks"]

            # return error if not enough peaks are detected
            if len(peak_loss) < 6:
                self.hrv_error.emit("Not enough peaks detected for HRV computation.")
                return

            # Calculate RMSSD, sdnn, mean_rr, and pnn50 using neurokit2
            hrv_results = nk.hrv_time(peaks, sampling_rate=self.sampling_rate, show=False)
            rmssd = float(hrv_results["HRV_RMSSD"].iloc[0])
            sdnn = float(hrv_results["HRV_SDNN"].iloc[0])
            mean_rr = float(hrv_results["HRV_MeanNN"].iloc[0])
            pnn50 = float(hrv_results["HRV_pNN50"].iloc[0])

            # Frequency domain 
            try: 
                hrv_freq_df = nk.hrv_frequency(peaks, sampling_rate=self.sampling_rate, show=False)
                self._hrv_freq = hrv_freq_df.iloc[0].to_dict()
                lf = float(hrv_freq_df["HRV_LF"].iloc[0])
                hf = float(hrv_freq_df["HRV_HF"].iloc[0])
                lf_hf = lf / hf if hf > 0 else float("nan")
            except Exception as e:
                print(f"  [DEBUG] hrv_frequency failed: {e}")  
                lf = float("nan")
                hf = float("nan")
                lf_hf = float("nan")
                self._hrv_freq = None

            # Nonlinear domain 
            try: 
                hrv_nonlinear_df = nk.hrv_nonlinear(peaks, sampling_rate=self.sampling_rate, show=False)
                self._hrv_nonlinear = hrv_nonlinear_df.iloc[0].to_dict()
                sd1 = float(hrv_nonlinear_df["HRV_SD1"].iloc[0])
                sd2 = float(hrv_nonlinear_df["HRV_SD2"].iloc[0])
            except Exception as e:
                print(f"  [DEBUG] hrv_nonlinear failed: {e}") 
                sd1 = float("nan")
                sd2 = float("nan")
                self._hrv_nonlinear = None

            # store RRI
            self._rri_ms = np.diff(peaks["PPG_Peaks"]) / self.sampling_rate * 1000 
            
            self.hrv_computed.emit({
                "rmssd":   rmssd,
                "sdnn":    sdnn,
                "mean_rr": mean_rr,
                "pnn50":   pnn50,
                "lf":      lf,
                "hf":      hf,
                "lf_hf":   lf_hf,
                "sd1":     sd1,
                "sd2":     sd2,
            })
            # send results
        except Exception as e:
            self.hrv_error.emit(f"Error processing data: {str(e)}")
            return
    
    # Open windows for RRI, Poincare, and PSD
    def open_rri_window(self, parent=None):
        win = RRIntervalWindow(self._rri_ms, parent)
        win.show()
        return win
    
    def open_poincare_window(self, parent=None):
        win = PoincarePlotWindow(self._rri_ms, self._hrv_nonlinear, parent)
        win.show()
        return win
    
    def open_psd_window(self, parent=None):
        win = PSDWindow(self._hrv_freq, parent)
        win.show()
        return win

    def set_sampling_rate(self, rate):
        self.sampling_rate = rate
        self.window_size = int(self.window_second * rate)
        self.buffer = []

    def set_window_seconds(self, seconds):
        self.window_second = seconds
        self.window_size = int(seconds * self.sampling_rate)
        self.buffer = []

# Function that calculates HRV and retunrs the result
def calculate_hrv(ppg_data, sampling_rate=256):
    processor = HRVProcessor(sampling_rate=sampling_rate)
    processor.window_size = len(ppg_data) # Set window size to the length of the data
    processor.buffer = list(ppg_data) # Load data into buffer

    restult = {}
    processor.hrv_computed.connect(lambda res: restult.update(res)) # Signal connection logic varies by usage
    processor.compute_hrv() 
    return restult


#Test output (Written by Claude AI)
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    print("=== Test 1: calculate_hrv() ===")
    ppg_data = nk.ppg_simulate(duration=60, sampling_rate=256, heart_rate=70)

    result = calculate_hrv(ppg_data, sampling_rate=256)

    if result:
        print(f"RMSSD: {result['rmssd']} ms")
        print("Test 1 PASSED")
    else:
        print("Test 1 FAILED - no results returned")

    print("\n=== Test 2: Chunked streaming ===")
    processor = HRVProcessor(sampling_rate=256, window_second=30)

    received = []
    errors = []
    processor.hrv_computed.connect(lambda r: received.append(r))
    processor.hrv_error.connect(lambda e: errors.append(e))

    chunk_size = 256
    for i in range(0, len(ppg_data), chunk_size):
        chunk = ppg_data[i:i + chunk_size].tolist()
        processor.receive_data(chunk)

    if received:
        print(f"Got {len(received)} HRV updates")
        print(f"Latest RMSSD: {received[-1]['rmssd']} ms")
        print("Test 2 PASSED")
    else:
        print(f"Test 2 FAILED - errors: {errors}")

    print("\n=== Test 3: Too little data ===")
    short_data = nk.ppg_simulate(duration=3, sampling_rate=256, heart_rate=70)
    result = calculate_hrv(short_data, sampling_rate=256)

    if not result:
        print("Correctly returned empty result for short data")
        print("Test 3 PASSED")
    else:
        print(f"Got result: {result}")
        print("Test 3 NOTE - short data still produced a result")

    print("\n=== Test 4: Reset ===")
    processor.reset()
    print("Test 4 PASSED" if len(processor.buffer) == 0 else "Test 4 FAILED - buffer not empty")

    # === Test 5: Plot Windows ===
    # === Test 5: Plot Windows ===
    print("\n=== Test 5: Plot Windows ===")

    # Use 256 Hz with 60s of data — enough for frequency domain
    ppg_data_long = nk.ppg_simulate(duration=60, sampling_rate=256, heart_rate=70)

    plot_processor = HRVProcessor(sampling_rate=256, window_second=60)
    plot_processor.hrv_computed.connect(lambda r: print(f"  HRV computed: RMSSD={r['rmssd']:.1f} ms, SD1={r['sd1']:.1f}, LF/HF={r['lf_hf']:.2f}"))
    plot_processor.hrv_error.connect(lambda e: print(f"  HRV error: {e}"))

    # Feed all data at once so compute_hrv() is called synchronously before we check
    plot_processor.buffer = ppg_data_long.tolist()
    plot_processor.window_size = len(plot_processor.buffer)
    plot_processor.compute_hrv()  # called directly, no async

    # Now _rri_ms and _hrv_freq are guaranteed to be populated
    print(f"  _rri_ms length: {len(plot_processor._rri_ms)}")
    print(f"  _hrv_freq populated: {plot_processor._hrv_freq is not None}")

    if len(plot_processor._rri_ms) > 1:
        rri_win      = plot_processor.open_rri_window()
        poincare_win = plot_processor.open_poincare_window()
        psd_win      = plot_processor.open_psd_window()
        print("Test 5 PASSED - close the windows to exit")
        sys.exit(app.exec())
    else:
        print("Test 5 FAILED - no RRI data computed")
        sys.exit(1)