import numpy as np
import neurokit2 as nk
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QApplication
import sys

# Gernerates simulated PPG and EDA data
class RawDataThread(QThread):
    # Chunk of PPG and EDA data
    ppg_ready = pyqtSignal(list)
    eda_ready = pyqtSignal(list)

    def __init__(self, sampling_rate=1000, chunk_second=1, parent=None):
        super().__init__(parent)
        self.sampling_rate = sampling_rate
        self.chunk_size = int(chunk_second * sampling_rate)
        self.running = True

    #simulates EDA and PPG data
    def run(self):
        self._running = True
        sim_duration = 120 # 2 minutes of data

        # Simulate PPG and EDA data
        ppg_data = nk.ppg_simulate(duration=sim_duration,
                                    sampling_rate=self.sampling_rate,
                                    heart_rate=70,)
            
        eda_data = nk.eda_simulate(duration=30, 
                        sampling_rate=self.sampling_rate, 
                        scr_number=20, 
                        drift=0.1, 
                        noise=0.01)

        total_samples = len(ppg_data)
        index = 0

        sleep_ms = int(1000 * (self.chunk_size / self.sampling_rate))

        while self._running: 
            if index + self.chunk_size > total_samples:
                index = 0

            ppg_chunk = ppg_data[index : index + self.chunk_size].tolist()
            eda_chunk = eda_data[index : index + self.chunk_size].tolist()

            self.ppg_ready.emit(ppg_chunk)
            self.eda_ready.emit(eda_chunk)

            index += self.chunk_size
            self.msleep(sleep_ms)

    def stop(self):
        self._running = False

#Test output (Written by Claude AI)
if __name__ == "__main__":
    app = QApplication(sys.argv)

    raw_thread = RawDataThread(sampling_rate=1000, chunk_second=1)

    # track what we receive
    ppg_count = [0]
    eda_count = [0]

    def on_ppg(chunk):
        ppg_count[0] += 1
        print(f"PPG chunk #{ppg_count[0]}: {len(chunk)} samples, "
              f"first={chunk[0]:.4f}, last={chunk[-1]:.4f}")

    def on_eda(chunk):
        eda_count[0] += 1
        print(f"EDA chunk #{eda_count[0]}: {len(chunk)} samples, "
              f"first={chunk[0]:.4f}, last={chunk[-1]:.4f}")

    raw_thread.ppg_ready.connect(on_ppg)
    raw_thread.eda_ready.connect(on_eda)

    # start streaming
    raw_thread.start()
    print("Streaming started... waiting 5 seconds\n")

    # stop after 5 seconds
    def finish():
        raw_thread.stop()
        raw_thread.wait()
        print(f"\nDone!")
        print(f"Total PPG chunks received: {ppg_count[0]}")
        print(f"Total EDA chunks received: {eda_count[0]}")

        # basic checks
        assert ppg_count[0] >= 4, "Should have received at least 4 PPG chunks"
        assert eda_count[0] >= 4, "Should have received at least 4 EDA chunks"
        assert ppg_count[0] == eda_count[0], "PPG and EDA chunk counts should match"
        print("All checks passed!")

        app.quit()

    QTimer.singleShot(5000, finish)
    app.exec_()