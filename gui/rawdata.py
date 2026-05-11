# Required pip installs:
# pip install pyserial
# pip install PySide6

import sys
import time
import serial
import serial.tools.list_ports
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QApplication

# Check for correct serial library (pyserial vs serial)
if not hasattr(serial, 'Serial'):
    print("\nCRITICAL ERROR: Incorrect 'serial' library detected.")
    print("Please run: pip uninstall serial && pip install pyserial\n")
    sys.exit(1)

def get_available_ports():
    try:
        return [port.device for port in serial.tools.list_ports.comports()]
    except Exception as e:
        print(f"Error listing ports: {e}")
        return []

# --- DATA STRUCTURES ---

@dataclass
class EDAData:
    raw: float
    smooth: float

@dataclass
class IMUData:
    ax: float; ay: float; az: float
    gx: float; gy: float; gz: float
    roll: float; pitch: float; yaw: float

@dataclass
class CardiacData:
    ir_value: int
    bpm: float
    hrv: float

@dataclass
class SensorPacket:
    timestamp: float
    eda: Optional[EDAData] = None
    imu: Optional[IMUData] = None
    cardiac: Optional[CardiacData] = None

# --- INGESTION NODE ---

class HardwareIngestionThread(QThread):
    """
    Central hub for reading, parsing, and routing live hardware data.
    """
    # Emits a fully parsed, time-synced packet of the wearable's state
    packet_ready = Signal(SensorPacket)
    # Emits error messages for the UI status bar
    error_occurred = Signal(str)

    def __init__(self, port: str = "COM4", baudrate: int = 115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self._running = True
        self.serial_conn = None

    def adc_to_microsiemens(self, adc_val: float, v_ref: float = 3.3, adc_res: int = 4095, r_series: float = 10000.0) -> float:
        """
        Converts raw ADC values to Conductance in microSiemens (µS).
        Assumes a voltage divider circuit where V_out is measured across R_series.
        """
        if adc_val <= 0 or adc_val >= adc_res:
            return 0.0
            
        v_out = (adc_val / adc_res) * v_ref
        try:
            r_skin = r_series * ((v_ref / v_out) - 1.0)
            conductance_us = 1_000_000.0 / r_skin
            return conductance_us
        except ZeroDivisionError:
            return 0.0

    def run(self):
        
        try:
            # Open the serial port with a timeout so the thread can exit gracefully
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"Connected to {self.port} at {self.baudrate} baud.")
        except serial.SerialException as e:
            self.error_occurred.emit(f"Failed to connect to hardware: {e}")
            self._running = False
            return

        # Clear any garbage data sitting in the buffer from before connection
        self.serial_conn.reset_input_buffer()

        while self._running:
            try:
                # Eagerly block and read the next line from the ESP32
                raw_line = self.serial_conn.readline()
                
                if not raw_line:
                    continue # Timeout reached, loop again

                decoded_line = raw_line.decode('utf-8', errors='ignore').strip()
                
                if not decoded_line:
                    continue

                # Parse and emit
                packet = self._parse_telemetry(decoded_line)
                if packet:
                    self.packet_ready.emit(packet)

            except Exception as e:
                self.error_occurred.emit(f"Serial read error: {e}")
                time.sleep(0.1) # Prevent CPU thrashing on consecutive errors

        # Cleanup on exit
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def _parse_telemetry(self, line: str) -> Optional[SensorPacket]:
        """
        Parses the ESP32 hardware output format:
        "GSR raw=2668 smooth=2669.74 | IR=0 | ACC=0.07,-0.01,1.02 | GYRO=-0.06,-0.06,0.00 | ANG=-0.50,-4.32,94.11"

        BPM and HRV are computed by the GUI's PPGProcessor/HRVProcessor, not the device.
        """
        try:
            packet = SensorPacket(timestamp=time.time())
            sections = [s.strip() for s in line.split('|')]
            imu_parts = {}

            for section in sections:
                if section.startswith("GSR"):
                    # "GSR raw=2668 smooth=2669.74"
                    raw_val = smooth_val = None
                    for part in section.split():
                        if part.startswith("raw="):
                            raw_adc = float(part.split('=')[1])
                            raw_val = self.adc_to_microsiemens(raw_adc)
                        elif part.startswith("smooth="):
                            smooth_adc = float(part.split('=')[1])
                            smooth_val = self.adc_to_microsiemens(smooth_adc)
                    if raw_val is not None and smooth_val is not None:
                        packet.eda = EDAData(raw=raw_val, smooth=smooth_val)

                elif section.startswith("IR="):
                    packet.cardiac = CardiacData(
                        ir_value=int(section.split('=')[1]),
                        bpm=0.0,
                        hrv=0.0
                    )

                elif section.startswith("ACC="):
                    vals = section[4:].split(',')
                    if len(vals) == 3:
                        imu_parts['acc'] = (float(vals[0]), float(vals[1]), float(vals[2]))

                elif section.startswith("GYRO="):
                    vals = section[5:].split(',')
                    if len(vals) == 3:
                        imu_parts['gyro'] = (float(vals[0]), float(vals[1]), float(vals[2]))

                elif section.startswith("ANG="):
                    vals = section[4:].split(',')
                    if len(vals) == 3:
                        imu_parts['ang'] = (float(vals[0]), float(vals[1]), float(vals[2]))

            if len(imu_parts) == 3:
                acc, gyro, ang = imu_parts['acc'], imu_parts['gyro'], imu_parts['ang']
                packet.imu = IMUData(
                    ax=acc[0], ay=acc[1], az=acc[2],
                    gx=gyro[0], gy=gyro[1], gz=gyro[2],
                    roll=ang[0], pitch=ang[1], yaw=ang[2]
                )

            if packet.eda or packet.imu or packet.cardiac:
                return packet
            return None

        except (ValueError, IndexError):
            return None

    def stop(self):
        self._running = False
        self.wait()

# --- STANDALONE TESTING ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Note: Change "COM3" to your actual ESP32 port (e.g., "/dev/ttyUSB0" on Linux)
    ingestion_node = HardwareIngestionThread(port="COM4", baudrate=115200)

    packet_count = [0]
    print(f"Using Standalone Testing Mode")

    def on_packet_received(packet: SensorPacket):
        packet_count[0] += 1
        print(f"Packet #{packet_count[0]} Received:")
        if packet.eda:
            print(f"  -> EDA: Raw={packet.eda.raw}, Smooth={packet.eda.smooth}")
        if packet.cardiac:
            print(f"  -> Cardiac: IR={packet.cardiac.ir_value}")
        if packet.imu:
            print(f"  -> IMU: ACC=({packet.imu.ax:.2f},{packet.imu.ay:.2f},{packet.imu.az:.2f}) "
                  f"ANG=({packet.imu.roll:.2f},{packet.imu.pitch:.2f},{packet.imu.yaw:.2f})")

    def on_error(msg: str):
        print(f"SYSTEM ERROR: {msg}")

    ingestion_node.packet_ready.connect(on_packet_received)
    ingestion_node.error_occurred.connect(on_error)

    ingestion_node.start()
    print("Ingestion node online... waiting for hardware stream.\n")

    def shutdown():
        ingestion_node.stop()
        print(f"\nIngestion node shut down safely. Total packets processed: {packet_count[0]}")
        app.quit()

    # Run test for 10 seconds
    QTimer.singleShot(10000, shutdown)
    sys.exit(app.exec())