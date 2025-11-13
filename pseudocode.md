# End-to-End Data Pipeline Architecture

Wearables Biosensor Platform
Generated 2025

This document describes the full software data pipeline for the biosensor research platform. It outlines how data flows across firmware, backend ingestion, signal processing, database storage, and the desktop GUI.

The pseudocode is language-agnostic but matches the actual toolchain: PlatformIO (C++), FastAPI (Python), TimescaleDB, and PySide6 with PyQtGraph.

---

# 1. Firmware (C++ PlatformIO)

Sensor Sampling and Serial Transmission

```pseudocode
// Runs on microcontroller (C++ with PlatformIO)

struct SensorPacket:
    uint32 timestamp_ms
    float eda_raw
    float ppg_raw

function setup:
    init_eda_sensor()
    init_ppg_sensor()
    Serial.begin(BAUD_RATE)

function loop:
    pkt = SensorPacket()

    pkt.timestamp_ms = millis()
    pkt.eda_raw      = read_eda_sensor()
    pkt.ppg_raw      = read_ppg_sensor()

    line = encode_as_json(pkt)
    Serial.println(line)

    delay_until_next_sample()
```

---

# 2. Backend System (FastAPI, Uvicorn, asyncio)

Asynchronous Ingestion, Processing, Storage, and Streaming

## Backend Queues

```pseudocode
queue_raw_samples       = AsyncQueue()
queue_processed_samples = AsyncQueue()
queue_db_writes         = AsyncQueue()
connected_clients       = set()
```

## Startup Routine

```pseudocode
async function on_startup:
    db_conn = init_timescaledb_connection()
    create_timescaledb_schema_if_needed(db_conn)

    spawn_task(serial_reader_task())
    spawn_task(signal_processing_task())
    spawn_task(db_writer_task(db_conn))
    spawn_task(websocket_broadcast_task())
```

---

## 2.1 Serial Reader (pyserial-asyncio-fast)

```pseudocode
async function serial_reader_task:
    port = await open_async_serial_port(PORT_NAME, BAUD_RATE)

    while true:
        line = await port.readline_async()
        if not valid_json(line):
            continue

        pkt = parse_json_to_packet(line)

        raw_sample = {
            "timestamp": pkt.timestamp_ms,
            "eda_raw":   pkt.eda_raw,
            "ppg_raw":   pkt.ppg_raw
        }

        await queue_raw_samples.put(raw_sample)
```

---

## 2.2 Signal Processing Pipeline

NeuroKit2 • Wavelet Denoising • HRV Extraction

```pseudocode
async function signal_processing_task:
    window_eda = RingBuffer(N_EDA_SAMPLES)
    window_ppg = RingBuffer(N_PPG_SAMPLES)

    while true:
        raw_sample = await queue_raw_samples.get()
        window_eda.append(raw_sample.eda_raw)
        window_ppg.append(raw_sample.ppg_raw)

        if window_eda.is_full() and window_ppg.is_full():
            eda_denoised = denoise_wavelet_1d(window_eda)
            ppg_denoised = denoise_wavelet_1d(window_ppg)

            eda_features = neurokit_eda_features(eda_denoised)
            hrv_features = neurokit_hrv_features_from_ppg(ppg_denoised)

            processed = {
                "timestamp":   raw_sample.timestamp,
                "eda_raw":     raw_sample.eda_raw,
                "ppg_raw":     raw_sample.ppg_raw,
                "eda_tonic":   eda_features.tonic,
                "eda_phasic":  eda_features.phasic,
                "hr":          hrv_features.heart_rate,
                "hrv_sdnn":    hrv_features.sdnn,
                "hrv_rmssd":   hrv_features.rmssd
            }

            await queue_processed_samples.put(processed)
            await queue_db_writes.put(processed)
```

---

## 2.3 TimescaleDB Writer (psycopg2-binary)

```pseudocode
async function db_writer_task(db_conn):
    batch = []

    while true:
        sample = await queue_db_writes.get()
        batch.append(sample)

        if batch.size >= BATCH_SIZE or time_since_last_flush() > MAX_INTERVAL:
            buffer = convert_samples_to_copy_format(batch)

            db_conn.copy_from(
                buffer,
                table="biosensor_readings",
                columns=[
                    "timestamp",
                    "eda_raw", "ppg_raw",
                    "eda_tonic", "eda_phasic",
                    "hr", "hrv_sdnn", "hrv_rmssd"
                ]
            )

            db_conn.commit()
            batch.clear()
            reset_last_flush_time()
```

---

## 2.4 FastAPI Endpoints

Historical Queries and Live WebSocket Streaming

```pseudocode
@app.get("/data")
async function get_data(start_time, end_time, channels):
    sql = """
        SELECT timestamp, eda_raw, ppg_raw,
               eda_tonic, eda_phasic,
               hr, hrv_sdnn, hrv_rmssd
        FROM biosensor_readings
        WHERE timestamp BETWEEN :start AND :end
        ORDER BY timestamp
    """
    rows = db_query(sql, params)
    return rows


@app.websocket("/ws/live")
async function websocket_endpoint(ws):
    await ws.accept()
    connected_clients.add(ws)

    try:
        while true:
            msg = await ws.receive_text_optional()
            handle_gui_control_message(msg)
    except WebSocketDisconnect:
        connected_clients.remove(ws)
```

---

## 2.5 WebSocket Broadcasting Loop

```pseudocode
async function websocket_broadcast_task:
    while true:
        sample = await queue_processed_samples.get()
        msg = serialize_to_json(sample)

        for ws in copy_of(connected_clients):
            try:
                await ws.send_text(msg)
            except WebSocketError:
                connected_clients.remove(ws)
```

---

# 3. GUI Client (PySide6 + PyQtGraph)

```pseudocode
class LivePlotWindow(QMainWindow):

    function __init__:
        setup_ui()
        self.eda_plot = PyQtGraphPlotWidget()
        self.ppg_plot = PyQtGraphPlotWidget()
        self.metric_labels = {
            "hr": QLabel(),
            "hrv_sdnn": QLabel(),
            "hrv_rmssd": QLabel()
        }

        self.websocket_client = LiveWebSocketClient("ws://localhost:8000/ws/live")
        self.websocket_client.on_message = self.handle_new_sample
        self.websocket_client.connect_async()

    function handle_new_sample(msg_json):
        sample = parse_json(msg_json)

        self.eda_plot.append_point(sample.timestamp, sample.eda_raw)
        self.ppg_plot.append_point(sample.timestamp, sample.ppg_raw)

        self.metric_labels["hr"].setText(str(sample.hr))
        self.metric_labels["hrv_sdnn"].setText(str(sample.hrv_sdnn))

        self.eda_plot.trim_to_last_seconds(SECONDS_VISIBLE)
        self.ppg_plot.trim_to_last_seconds(SECONDS_VISIBLE)

function main_gui:
    app = QApplication()
    win = LivePlotWindow()
    win.show()
    app.exec()
```

---

# 4. CI and Monorepo Workflow (GitHub Actions)

```pseudocode
on_push_or_pr:

    if files_changed_in("firmware"):
        job build_firmware:
            setup_platformio()
            platformio run
            save_artifact(firmware_binary)

    if files_changed_in("backend"):
        job test_backend:
            pip install backend requirements
            run_unit_tests backend
            run_lint backend

    if files_changed_in("gui"):
        job test_gui:
            pip install gui requirements
            run_unit_tests gui
```

---

# 5. Full Data Flow Summary

1. Firmware samples sensors, packages data, sends JSON lines over serial.
2. Backend asynchronously reads serial via asyncio without blocking FastAPI.
3. Data enters raw queue and is processed:

   * Wavelet denoising
   * EDA tonic and phasic extraction
   * HR and HRV computation
4. Processed data is written to TimescaleDB in large batched inserts.
5. The same processed data is streamed to GUI clients via WebSockets.
6. PySide6 GUI displays plots and live metrics using PyQtGraph.

---

End of document.
