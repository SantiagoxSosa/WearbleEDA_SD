import asyncio
import struct
from bleak import BleakScanner, BleakClient

#Conect the BLE device
DEVICE_NAME = "Device"
CHAR_UUID = "12345678-1234-1234-1234-1234567890ac"

class BLEClient:
    def __init__(self, on_data_callback):
        self.on_data = on_data_callback

    async def run(self):
        print("Scanning for BLE device...")
        device = await BleakScanner.find_device_by_filter(
            lambda d, ad: d.name == DEVICE_NAME
        ) 
        if device is None:
            print(f"No BLE device named '{DEVICE_NAME}' found.")
            return 

        async with BleakClient(device) as client:
            print("Connected to BLE device")

            def notify_handler(sender, data):
                self.on_data(bytes(data))

            await client.start_notify(CHAR_UUID, notify_handler)

            while True:
                await asyncio.sleep(1)

#Format
#temperature, humidity, battery
FMT = "<hHHH"

#Decoder
def decode(data: bytes) -> dict | None: 
    temp, hum, batt = struct.unpack(FMT, data)
    return { 
        "temperature": temp,
        "humidity": hum,
        "battery": batt
    }

#decodes packet
def decode_packet(raw_bytes: bytes):
    decoded = decode(raw_bytes)
    return decoded

async def main(): 
    ble = BLEClient(on_data_callback=decode_packet)
    await ble.run()

if __name__ == "__main__": 
    asyncio.run(main())