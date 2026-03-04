import numpy as np
import neurokit2 as nk
from PySide6.QtCore import QObject

class PPGProcessor(QObject):
    """
    Processes Cardiac data (PPG) to extract Heart Rate.
    """
    def __init__(self, parent=None, sampling_rate=20, window_seconds=10):
        super().__init__(parent)
        self.sampling_rate = sampling_rate
        self.window_seconds = window_seconds
        self.window_size = int(window_seconds * sampling_rate)
        self.buffer = []
        self.current_bpm = 0.0
        self.smoothed_bpm = 0.0

    def process_batch(self, packets: list) -> list[float]:
        """
        Takes a list of SensorPackets and returns list of Heart Rate values.
        
        Args:
            packets (list): A list of SensorPacket objects containing raw data.
            
        Returns:
            list[float]: A list of Heart Rate (BPM) values.
        """
        new_values = []
        for p in packets:
            val = 0.0
            if p.cardiac:
                val = float(p.cardiac.ir_value)
            new_values.append(val)
        
        self.buffer.extend(new_values)
        
        # Maintain buffer size
        if len(self.buffer) > self.window_size:
            self.buffer = self.buffer[-self.window_size:]
            
        # Compute BPM curve for the new data points
        bpm_curve = []
        if len(self.buffer) >= self.sampling_rate * 2:
             bpm_curve = self._compute_bpm_curve(len(new_values))
            
        if not bpm_curve:
            bpm_curve = [self.current_bpm] * len(new_values)
            
        # Apply smoothing to avoid square wave steps
        smoothed_curve = []
        alpha = 0.05 # Smoothing factor
        
        for val in bpm_curve:
            if self.smoothed_bpm == 0.0 and val > 0:
                self.smoothed_bpm = val
            self.smoothed_bpm = self.smoothed_bpm * (1 - alpha) + val * alpha
            smoothed_curve.append(self.smoothed_bpm)
            
        return smoothed_curve

    def _compute_bpm_curve(self, num_new):
        try:
            # Clean signal
            clean_signal = nk.ppg_clean(self.buffer, sampling_rate=self.sampling_rate)
            
            # Find peaks
            info = nk.ppg_findpeaks(clean_signal, sampling_rate=self.sampling_rate)
            peaks = info["PPG_Peaks"]
            
            if len(peaks) >= 2:
                # Calculate instantaneous rate
                rate = nk.signal_rate(peaks, sampling_rate=self.sampling_rate, desired_length=len(self.buffer))
                
                # Get the last valid rate value
                valid_rates = rate[~np.isnan(rate)]
                if len(valid_rates) > 0:
                    self.current_bpm = valid_rates[-1]
                
                # Extract the tail corresponding to the new samples
                tail = rate[-num_new:]
                
                # Replace any NaNs in the tail with the last known valid BPM to avoid gaps
                tail = np.where(np.isnan(tail), self.current_bpm, tail)
                
                return tail.tolist()
        except Exception:
            # Fail silently or log, keep last known BPM
            pass
        return []

    def set_sampling_rate(self, rate):
        self.sampling_rate = rate
        self.window_size = int(self.window_seconds * rate)
        self.buffer = []

    def set_window_seconds(self, seconds):
        self.window_seconds = seconds
        self.window_size = int(seconds * self.sampling_rate)
        self.buffer = []