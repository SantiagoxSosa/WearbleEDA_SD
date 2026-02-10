import neurokit2 as nk
import pandas as pd
import matplotlib.pyplot as plt



eda_signal = nk.eda_simulate(duration=30, 
                             sampling_rate=1000, 
                             scr_number=5, 
                             drift=0.1, 
                             noise=0.01)

# 2. Process the signal
# This decomposes into Phasic/Tonic and identifies SCR onsets/peaks
signals, info = nk.eda_process(eda_signal, sampling_rate=1000)



# 3. Plot the results
# eda_plot automatically visualizes the Raw, Filtered, Phasic, and Tonic signals
# It also marks the SCR onsets (red dashed) and peaks (blue dots)
nk.eda_plot(signals, info)

# Display
plt.show()