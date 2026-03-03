from PySide6.QtCore import QObject

class PPGProcessor(QObject):
    """
    Processes Cardiac data (PPG) to extract Heart Rate.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def process_batch(self, packets):
        """
        Takes a list of SensorPackets and returns list of Heart Rate values.
        """
        hr_values = []
        
        for packet in packets:
            val = packet.cardiac.bpm if packet.cardiac else 0.0
            hr_values.append(val)
            
        return hr_values