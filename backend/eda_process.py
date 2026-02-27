# backend/eda_process.py
import numpy as np
import neurokit2 as nk

def process_eda(raw_eda, sampling_rate_hz, method="neurokit"):
    """
    input: 1D array of raw EDA signals (window)
    output: returns arrays of tonic and phasic components
    """

    # acquire signal
    eda = np.asarray(raw_eda, dtype=float)

    # clean signal with low-pass and butterworth filters
    eda_cleaned = nk.eda_clean(eda, sampling_rate=sampling_rate_hz, method="neurokit")

    # decompose into tonic and phasic components
    eda_proc = nk.eda_phasic(eda_cleaned, sampling_rate=sampling_rate_hz, method=method)
    tonic = np.asarray(eda_proc["EDA_Tonic"], dtype=float)
    phasic = np.asarray(eda_proc["EDA_Phasic"], dtype=float)

    return tonic, phasic

def detect_stress(phasic, sampling_rate_hz):
    """
    input: 1D array of EDA phasic component
    output: inidices of stress responses in array
    """

    # eda_peaks requires the phasic component only
    signals, info = nk.eda_peaks(phasic, sampling_rate=sampling_rate_hz)

    # neurokit returns indices as (peaks, onsets)
    onsets = info.get("SCR_Onsets", [])
    peaks = info.get("SCR_Peaks", [])

    return list(onsets), list(peaks)