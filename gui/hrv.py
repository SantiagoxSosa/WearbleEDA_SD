import neurokit2 as nk
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

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

            # Calculate RMSSD using neurokit2
            hrv_results = nk.hrv_time(peaks, sampling_rate=self.sampling_rate, show=False)
            rmssd = float(hrv_results["HRV_RMSSD"].iloc[0])
           
            self.hrv_computed.emit({"rmssd": rmssd})
            # send results
        except Exception as e:
            self.hrv_error.emit(f"Error processing data: {str(e)}")
            return

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
    # processor.hrv_computed.connect(lambda res: restult.update(res)) # Signal connection logic varies by usage
    processor.compute_hrv() 
    return restult

#Test output (Written by Claude AI)
if __name__ == "__main__": 
    print("=== Test 1: calculate_hrv() ===")
    # simulate 60 seconds of PPG data at 256 Hz with ~70 bpm heart rate
    ppg_data = nk.ppg_simulate(duration=60, sampling_rate=256, heart_rate=70)

    result = calculate_hrv(ppg_data, sampling_rate=256)

    if result:
        print(f"RMSSD: {result['rmssd']} ms")
        print("Test 1 PASSED")
    else:
        print("Test 1 FAILED - no results returned")
    print("\n=== Test 2: Chunked streaming ===")

    processor = HRVProcessor(sampling_rate=256, window_second=30)

    # store results as they come in
    received = []
    errors = []
    processor.hrv_computed.connect(lambda r: received.append(r))
    processor.hrv_error.connect(lambda e: errors.append(e))

    # simulate sending data in small chunks (like real streaming would)
    # 256 samples = 1 second of data
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


    # --- Test 3: Not enough data (should error gracefully) ---
    print("\n=== Test 3: Too little data ===")

    short_data = nk.ppg_simulate(duration=3, sampling_rate=256, heart_rate=70)
    result = calculate_hrv(short_data, sampling_rate=256)

    if not result:
        print("Correctly returned empty result for short data")
        print("Test 3 PASSED")
    else:
        print(f"Got result: {result}")
        print("Test 3 NOTE - short data still produced a result")


    # --- Test 4: Reset works ---
    print("\n=== Test 4: Reset ===")

    processor.reset()

    if len(processor.buffer) == 0:
        print("Buffer cleared successfully")
        print("Test 4 PASSED")
    else:
        print("Test 4 FAILED - buffer not empty")