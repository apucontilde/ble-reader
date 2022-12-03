import simplepyble
import time
import sys
import traceback
import logging


GOVEE_H5101_UUID = "a4:c1:38:b4:20:46"


def parse_data(data: bytearray):
    basenum = (int(data[2]) << 16) + (int(data[3]) << 8) + int(data[4])
    temperature = basenum / 10000.0
    humidity = (basenum % 1000) / 10.0
    battery_level = int(data[5]) / 1.0
    print(f"humidity: {humidity} %")
    print(f"temperature: {temperature} °C")
    print(f"battery: {battery_level} %")
    return humidity, temperature, battery_level


if __name__ == "__main__":
    adapters = simplepyble.Adapter.get_adapters()

    if len(adapters) == 0:
        print("No adapters found")
        sys.exit()

    adapter = adapters[0]

    print(f"Selected adapter: {adapter.identifier()} [{adapter.address()}]")

    # Scan for 5 seconds
    adapter.scan_for(15000)
    peripherals = adapter.scan_get_results()
    chosen_peripheral = None
    for i, peripheral in enumerate(peripherals):
        if peripheral.address() == GOVEE_H5101_UUID:
            chosen_peripheral = peripheral

    if not chosen_peripheral:
        print(f"No peripheral found with id: {GOVEE_H5101_UUID}")
        sys.exit()
    print(
        f"Connecting to: {chosen_peripheral.identifier()} [{chosen_peripheral.address()}]"
    )
    chosen_peripheral.connect()

    print("Successfully connected, listing services...")
    services = chosen_peripheral.services()
    service_characteristic_pair = []
    characteristics = {}
    for service in services:
        for characteristic in service.characteristics():
            service_characteristic_pair.append((service.uuid(), characteristic.uuid()))
            characteristics[characteristic.uuid()] = characteristic

    print(f"reading characteristics...")
    subscribed = None
    for i, (service_uuid, characteristic_uuid) in enumerate(
        service_characteristic_pair
    ):
        try:
            value = chosen_peripheral.read(
                service_uuid,
                characteristic_uuid,
            )
            characteristic = characteristics[characteristic_uuid]

            can_notify = (
                characteristic.can_notify()
                if hasattr(characteristic, "can_notify")
                else False
            )

            can_indicate = (
                characteristic.can_indicate()
                if hasattr(characteristic, "can_indicate")
                else False
            )

            print(f"{service_uuid}:{characteristic_uuid}:")
            print(f"can_notify: {can_notify} can_indicate: {can_indicate}")
            if len(value) == 7:  # H5051
                print(f"data ({len(value)}): {value}\n{value.hex()}")
                humidity, temperature, battery_level = parse_data(value)
                if can_notify:
                    chosen_peripheral.notify(
                        service_uuid, characteristic_uuid, parse_data
                    )
                    subscribed = (service_uuid, characteristic_uuid)
        except Exception:
            logging.exception(f"Error while reading or subscribing")
    time.sleep(10)
    if subscribed:
        service_uuid, characteristic_uuid = subscribed
        chosen_peripheral.unsubscribe(service_uuid, characteristic_uuid)
    chosen_peripheral.disconnect()
