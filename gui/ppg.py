import neurokit2 as nk
import pandas as pd
import matplotlib.pyplot as plt



ppg_signal = nk.ppg_simulate(duration=30,
                                        sampling_rate=1000,
                                        heart_rate=70,
        )

# 2. Process the signal
# This decomposes into Phasic/Tonic and identifies SCR onsets/peaks
signals, info = nk.ppg_process(ppg_signal, sampling_rate=1000)



# 3. Plot the results
# eda_plot automatically visualizes the Raw, Filtered, Phasic, and Tonic signals
# It also marks the SCR onsets (red dashed) and peaks (blue dots)
nk.ppg_plot(signals, info)

# Display
plt.show()