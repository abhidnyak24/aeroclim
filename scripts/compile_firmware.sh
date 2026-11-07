#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
arduino-cli core update-index --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32@3.3.0 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli lib install 'ArduinoJson@7.4.3' 'PubSubClient@2.8.0' 'DHT sensor library@1.4.7' 'Adafruit Unified Sensor@1.1.15' 'Adafruit VEML7700 Library@2.1.6' 'Adafruit BusIO@1.17.4'
arduino-cli compile --fqbn esp32:esp32:esp32c6:CDCOnBoot=cdc firmware/AeroClimNode
