from PySide6.QtCore import QObject

class EDAProcessor(QObject):
    """
    Processes raw EDA data into Phasic and Tonic components.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def process_batch(self, packets):
        """
        Takes a list of SensorPackets and returns lists of processed values.
        Returns: (eda_smooth, phasic, tonic)
        """
        eda_values = []
        phasic_values = []
        tonic_values = []
        
        for packet in packets:
            val_smooth = 0.0
            val_phasic = 0.0
            val_tonic = 0.0

            if packet.eda:
                val_smooth = packet.eda.smooth
                val_tonic = packet.eda.smooth
                val_phasic = packet.eda.raw - packet.eda.smooth

            eda_values.append(val_smooth)
            phasic_values.append(val_phasic)
            tonic_values.append(val_tonic)
            
        return eda_values, phasic_values, tonic_values