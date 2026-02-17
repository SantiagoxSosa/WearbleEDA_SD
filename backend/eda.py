import neurokit2 as nk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class SimulateEDAStream:
    """
    Generate a simulated EDA signal, 
    processed once with neurokit,
    then streamed to GUI.

    raw: EDA_raw
    phasic: EDA_phasic
    tonic: EDA_tonic
    """
    def __init__(self, duration_s=30, sampling_rate_hz=1000, gui_rate_hz=20):
        self.fs = float(sampling_rate_hz)
        self.gui_fs = float(gui_rate_hz)

        eda_signal = nk.eda_simulate(
            duration = duration_s, 
            sampling_rate = sampling_rate_hz, 
            scr_number = 5, 
            drift = 0.1, 
            noise = 0.01
        )

        # 2. Process the signal
        # This decomposes into Phasic/Tonic and identifies SCR onsets/peaks
        signals, info = nk.eda_process(eda_signal, sampling_rate=sampling_rate_hz)

        # store arrays for raw, phasic, tonic
        self.raw = np.asarray(signals["EDA_Raw"])
        self.phasic = np.asarray(signals["EDA_Phasic"])
        self.tonic = np.asarray(signals["EDA_Tonic"])

        self.n = len(self.raw)

        # step size: how many 1000Hz samples per GUI tick (e.g., 1000/20 = 50)
        self.step = max(1, int(round(self.fs / self.gui_fs)))
        self.idx = 0

    def reset(self):
        self.idx = 0

    def next(self):
        """
        Returns a single sample : (raw, phasic, tonic)
        Loops when reaching the end
        """
        i = self.idx
        self.idx += self.step
        if self.idx >= self.n:
            self.idx = 0
        return float(self.raw[i]), float(self.phasic[i]), float(self.tonic[i])