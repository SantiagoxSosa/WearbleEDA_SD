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

    def __init__(self, port: str = "COM3", baudrate: int = 115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self._running = True
        self.serial_conn = None

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
        Expects a unified string format: 
        "EDA:4095,3000.5|IMU:1.0,0.5,0.1,2.0,2.1,2.2,45.0,30.0,10.0|HR:80000,72.5,45.2"
        """
        try:
            packet = SensorPacket(timestamp=time.time())
            sections = line.split('|')

            for section in sections:
                if section.startswith("EDA:"):
                    vals = section.replace("EDA:", "").split(',')
                    if len(vals) == 2:
                        packet.eda = EDAData(raw=float(vals[0]), smooth=float(vals[1]))
                
                elif section.startswith("IMU:"):
                    vals = section.replace("IMU:", "").split(',')
                    if len(vals) == 9:
                        packet.imu = IMUData(
                            ax=float(vals[0]), ay=float(vals[1]), az=float(vals[2]),
                            gx=float(vals[3]), gy=float(vals[4]), gz=float(vals[5]),
                            roll=float(vals[6]), pitch=float(vals[7]), yaw=float(vals[8])
                        )
                
                elif section.startswith("HR:"):
                    vals = section.replace("HR:", "").split(',')
                    if len(vals) == 3:
                        packet.cardiac = CardiacData(
                            ir_value=int(vals[0]), bpm=float(vals[1]), hrv=float(vals[2])
                        )
            
            # Ensure we actually parsed something before returning
            if packet.eda or packet.imu or packet.cardiac:
                return packet
            return None

        except (ValueError, IndexError) as e:
            # Fail silently on corrupted serial lines (common in live hardware streams)
            return None

    def stop(self):
        self._running = False
        self.wait()

# --- STANDALONE TESTING ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Note: Change "COM3" to your actual ESP32 port (e.g., "/dev/ttyUSB0" on Linux)
    ingestion_node = HardwareIngestionThread(port="COM3", baudrate=115200)

    packet_count = [0]
    print(f"Using Standalone Testing Mode")

    def on_packet_received(packet: SensorPacket):
        packet_count[0] += 1
        print(f"Packet #{packet_count[0]} Received:")
        if packet.eda:
            print(f"  -> EDA: Raw={packet.eda.raw}, Smooth={packet.eda.smooth}")
        if packet.cardiac:
            print(f"  -> Cardiac: BPM={packet.cardiac.bpm}, HRV={packet.cardiac.hrv}")

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