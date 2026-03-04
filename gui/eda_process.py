from PySide6.QtCore import QObject
import neurokit2 as nk
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class EDAProcessor(QObject):
    """
    Processes raw EDA data into Phasic and Tonic components.
    """
    def __init__(self, parent=None, sampling_rate=20, window_seconds=60):
        super().__init__(parent)
        self.sampling_rate = sampling_rate
        self.window_seconds = window_seconds
        self.window_size = int(window_seconds * sampling_rate)
        self.buffer = []

    def process_batch(self, packets: list) -> tuple[list[float], list[float], list[float]]:
        """
        Takes a list of SensorPackets and returns lists of processed values.
        
        Args:
            packets (list): A list of SensorPacket objects containing raw data.
            
        Returns:
            tuple: (eda_smooth, phasic, tonic)
                - eda_smooth (list[float]): Cleaned EDA signal.
                - phasic (list[float]): Phasic component (SCR).
                - tonic (list[float]): Tonic component (SCL).
        """
        # 1. Extract raw EDA values from packets
        new_raw = []
        for p in packets:
            val = 0.0
            if p.eda:
                val = float(p.eda.raw)
            new_raw.append(val)
        
        if not new_raw:
            return [], [], []

        # 2. Append to internal buffer
        self.buffer.extend(new_raw)
        
        # Keep buffer size fixed
        if len(self.buffer) > self.window_size:
            self.buffer = self.buffer[-self.window_size:]
            
        # 3. Process if buffer is sufficient size
        # We need enough history for the filters to settle (at least 4 seconds recommended)
        if len(self.buffer) >= self.sampling_rate * 4:
            try:
                # Run NeuroKit2 processing
                # method='neurokit' uses a high-pass filter for phasic extraction (fast & robust)
                signals, _ = nk.eda_process(self.buffer, sampling_rate=self.sampling_rate, method='neurokit')
                
                # Store for debug plotting
                self.last_signals = signals
                self.last_info = _
                
                # 4. Extract 'EDA_Clean', 'EDA_Phasic', 'EDA_Tonic'
                # We only need the values corresponding to the new packets we just added
                n_new = len(new_raw)
                
                # signals is a DataFrame. We take the last n_new rows.
                eda_clean = signals["EDA_Clean"].iloc[-n_new:].to_list()
                phasic = signals["EDA_Phasic"].iloc[-n_new:].to_list()
                tonic = signals["EDA_Tonic"].iloc[-n_new:].to_list()
                
                return eda_clean, phasic, tonic
                
            except Exception as e:
                print(f"EDA Processing Error: {e}")
                # Fallback on error
                return new_raw, [0.0]*len(new_raw), new_raw
        else:
            # Not enough data yet, return raw as smooth, 0 for components
            return new_raw, [0.0]*len(new_raw), new_raw

    def create_debug_plot(self):
        """
        Opens a matplotlib window with the NeuroKit2 analysis of the current buffer.
        Useful for verifying the signal processing pipeline.
        """
        if hasattr(self, 'last_signals') and hasattr(self, 'last_info'):
            # Create the plot using NeuroKit2's native function
            nk.eda_plot(self.last_signals, self.last_info)
            plt.show()

    def set_sampling_rate(self, rate):
        self.sampling_rate = rate
        self.window_size = int(self.window_seconds * rate)
        self.buffer = []

    def set_window_seconds(self, seconds):
        self.window_seconds = seconds
        self.window_size = int(seconds * self.sampling_rate)
        self.buffer = []