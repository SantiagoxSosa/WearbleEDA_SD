import numpy as np
import neurokit2 as nk
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication
import sys
import time
from dataclasses import dataclass
from typing import Optional
from rawdata import SensorPacket, EDAData, IMUData, CardiacData

# --- SIMULATION INGESTION NODE ---

class SimulationIngestionThread(QThread):
    """
    Generates simulated hardware data and emits it in the same format
    as the real HardwareIngestionThread.
    """
    packet_ready = Signal(SensorPacket)
    error_occurred = Signal(str)

    def __init__(self, sampling_rate=20, parent=None):
        super().__init__(parent)
        self.sampling_rate = sampling_rate
        self._running = True
        self.sim_duration = 120  # 2 minutes of data to loop through

    def _generate_data(self):
        """ Pre-computes all necessary data streams for the simulation. """
        num_samples = self.sim_duration * self.sampling_rate
        t = np.linspace(0, self.sim_duration, num_samples, endpoint=False)

        # --- Cardiac Data Simulation ---
        ppg_raw = nk.ppg_simulate(duration=self.sim_duration,
                                  sampling_rate=self.sampling_rate,
                                  heart_rate=75)
        ppg_signals, ppg_info = nk.ppg_process(ppg_raw, sampling_rate=self.sampling_rate)
        self.sim_ir_values = ppg_raw
        self.sim_bpm = ppg_signals["PPG_Rate"]
        # Create a plausible, smoothly varying HRV signal
        hrv_raw = nk.hrv_time(ppg_info["PPG_Peaks"], sampling_rate=self.sampling_rate, show=False)["HRV_RMSSD"].values
        hrv_indices = np.linspace(0, num_samples, len(hrv_raw))
        self.sim_hrv = np.interp(np.arange(num_samples), hrv_indices, hrv_raw)

        # --- EDA Data Simulation ---
        eda_raw = nk.eda_simulate(duration=self.sim_duration,
                                  sampling_rate=self.sampling_rate,
                                  scr_number=8,
                                  drift=0.05,
                                  noise=0.005)
        eda_signals, _ = nk.eda_process(eda_raw, sampling_rate=self.sampling_rate)
        self.sim_eda_raw = eda_raw
        self.sim_eda_smooth = eda_signals["EDA_Clean"]

        # --- IMU Data Simulation ---
        self.sim_imu_ax = 0.1 * np.sin(t * 1.5) + np.random.randn(num_samples) * 0.05
        self.sim_imu_ay = 0.1 * np.cos(t * 1.5) + np.random.randn(num_samples) * 0.05
        self.sim_imu_az = -9.8 + 0.05 * np.sin(t * 0.5)
        self.sim_imu_gx = 15 * np.sin(t * 2.5) + np.random.randn(num_samples) * 2
        self.sim_imu_gy = 15 * np.cos(t * 2.5) + np.random.randn(num_samples) * 2
        self.sim_imu_gz = 5 * np.sin(t * 0.8)
        # Integrate gyro for angle, just for show
        self.sim_imu_roll = np.cumsum(self.sim_imu_gx) / self.sampling_rate
        self.sim_imu_pitch = np.cumsum(self.sim_imu_gy) / self.sampling_rate
        self.sim_imu_yaw = np.cumsum(self.sim_imu_gz) / self.sampling_rate

        self.total_samples = num_samples

    def run(self):
        # Generate data in the background thread to avoid freezing the UI
        self._generate_data()
        
        index = 0
        sleep_ms = int(1000 / self.sampling_rate)

        while self._running: 
            if index >= self.total_samples:
                index = 0  # Loop the simulation data

            # Assemble data for the current time step into a SensorPacket
            try:
                cardiac = CardiacData(
                    ir_value=int(self.sim_ir_values[index] * 1000),
                    bpm=self.sim_bpm[index],
                    hrv=self.sim_hrv[index]
                )

                eda = EDAData(
                    raw=int(self.sim_eda_raw[index] * 1000),
                    smooth=self.sim_eda_smooth[index]
                )

                imu = IMUData(
                    ax=self.sim_imu_ax[index], ay=self.sim_imu_ay[index], az=self.sim_imu_az[index],
                    gx=self.sim_imu_gx[index], gy=self.sim_imu_gy[index], gz=self.sim_imu_gz[index],
                    roll=self.sim_imu_roll[index], pitch=self.sim_imu_pitch[index], yaw=self.sim_imu_yaw[index]
                )

                packet = SensorPacket(
                    timestamp=time.time(),
                    eda=eda,
                    imu=imu,
                    cardiac=cardiac
                )
                self.packet_ready.emit(packet)

            except Exception as e:
                self.error_occurred.emit(f"Simulation error: {e}")
                # Don't stop for a single bad data point
                
            index += 1
            self.msleep(sleep_ms)

    def stop(self):
        self._running = False
        self.wait()

#Test output (Written by Claude AI)
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Use the new simulation thread
    ingestion_node = SimulationIngestionThread(sampling_rate=20)

    # track what we receive
    packet_count = [0]
    print(f"Using Standalone Testing Mode for simdata.py")

    def on_packet_received(packet: SensorPacket):
        packet_count[0] += 1
        print(f"Packet #{packet_count[0]} Received:")
        if packet.eda:
            print(f"  -> EDA: Raw={packet.eda.raw}, Smooth={packet.eda.smooth:.3f}")
        if packet.cardiac:
            print(f"  -> Cardiac: BPM={packet.cardiac.bpm:.2f}, HRV={packet.cardiac.hrv:.2f}")
        if packet.imu:
            print(f"  -> IMU: ax={packet.imu.ax:.2f}, ay={packet.imu.ay:.2f}, az={packet.imu.az:.2f}")

    def on_error(msg: str):
        print(f"SYSTEM ERROR: {msg}")

    ingestion_node.packet_ready.connect(on_packet_received)
    ingestion_node.error_occurred.connect(on_error)

    # start streaming
    ingestion_node.start()
    print("Simulation node online... generating data stream.\n")

    # stop after 5 seconds
    def finish():
        ingestion_node.stop()
        print(f"\nDone!")
        print(f"Total packets processed: {packet_count[0]}")

        # basic checks
        assert packet_count[0] > 80, "Should have received many packets"
        print("All checks passed!")

        app.quit()

    QTimer.singleShot(5000, finish)
    sys.exit(app.exec())