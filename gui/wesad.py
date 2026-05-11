import os
import sys
import time
import numpy as np
import pandas as pd
import neurokit2 as nk
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication
from typing import Optional
from rawdata import SensorPacket, EDAData, IMUData, CardiacData

class WesadIngestionThread(QThread):
    """
    Ingests actual WESAD dataset CSV files (e.g. EDA.csv, BVP.csv),
    resamples them to a unified sampling rate, and emits simulated 
    real-time hardware packets for the GUI.
    """
    packet_ready = Signal(SensorPacket)
    error_occurred = Signal(str)

    def __init__(self, eda_csv_path: str, ppg_csv_path: str, sampling_rate=20, parent=None):
        super().__init__(parent)
        self.eda_csv_path = eda_csv_path
        self.ppg_csv_path = ppg_csv_path # WESAD uses BVP.csv for PPG
        self.sampling_rate = sampling_rate
        self._running = True

    def _load_e4_csv(self, filepath):
        """
        WESAD Empatica E4 CSV format:
        Row 1: Unix Timestamp (Start Time)
        Row 2: Sampling Rate (Hz)
        Row 3+: Signal Data
        """
        # Read just the first two rows to check for Empatica E4 metadata
        meta_df = pd.read_csv(filepath, header=None, nrows=2)
        
        # Check if the format matches Empatica E4 (first row is a timestamp > 1e9, second is a small float/int)
        if meta_df.iloc[0, 0] > 1e8 and meta_df.iloc[1, 0] < 1000:
            start_time = meta_df.iloc[0, 0]
            fs = meta_df.iloc[1, 0]
            signal_df = pd.read_csv(filepath, header=None, skiprows=2)
            signal = signal_df.iloc[:, 0].values
        else:
            # Fallback for standard single-column CSV
            df = pd.read_csv(filepath, header=None)
            start_time = time.time()
            fs = self.sampling_rate # assume same as target if not provided
            signal = df.iloc[:, 0].values
            
        return start_time, fs, signal

    def _generate_data(self):
        """ Pre-computes and aligns the data streams. """
        eda_start, eda_fs, eda_raw = self._load_e4_csv(self.eda_csv_path)
        ppg_start, ppg_fs, ppg_raw = self._load_e4_csv(self.ppg_csv_path)

        # Duration based on the shorter of the two signals
        eda_duration = len(eda_raw) / eda_fs
        ppg_duration = len(ppg_raw) / ppg_fs
        duration = min(eda_duration, ppg_duration)

        num_samples = int(duration * self.sampling_rate)

        # Resample both signals to the unified sampling rate
        self.eda_resampled = nk.signal_resample(eda_raw, desired_length=num_samples, 
                                                sampling_rate=eda_fs, desired_sampling_rate=self.sampling_rate)
        
        self.ppg_resampled = nk.signal_resample(ppg_raw, desired_length=num_samples, 
                                                sampling_rate=ppg_fs, desired_sampling_rate=self.sampling_rate)

        self.total_samples = num_samples

    def run(self):
        try:
            self._generate_data()
        except Exception as e:
            self.error_occurred.emit(f"Failed to process WESAD data: {e}")
            return
            
        index = 0
        sleep_ms = int(1000 / self.sampling_rate)

        while self._running:
            if index >= self.total_samples:
                index = 0  # Loop the playback
                
            try:
                # E4 BVP values are often floats, map to an integer arbitrary range mimicking IR value
                ir_val = int(self.ppg_resampled[index] * 1000) 
                
                cardiac = CardiacData(
                    ir_value=ir_val,
                    bpm=0.0,
                    hrv=0.0
                )

                eda = EDAData(
                    raw=self.eda_resampled[index],
                    smooth=self.eda_resampled[index]
                )

                # Mock IMU Data
                imu = IMUData(
                    ax=0.0, ay=0.0, az=-9.8,
                    gx=0.0, gy=0.0, gz=0.0,
                    roll=0.0, pitch=0.0, yaw=0.0
                )

                packet = SensorPacket(
                    timestamp=time.time(),
                    eda=eda,
                    imu=imu,
                    cardiac=cardiac
                )
                self.packet_ready.emit(packet)

            except Exception as e:
                self.error_occurred.emit(f"Playback error: {e}")
                
            index += 1
            self.msleep(sleep_ms)

    def stop(self):
        self._running = False
        self.wait()

    def set_sampling_rate(self, rate):
        self.sampling_rate = rate