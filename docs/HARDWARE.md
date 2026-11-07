# Hardware checks — before the fully connected power-on

The source notes are a description, not a verified PCB schematic. Pin names below are GPIO numbers, not a single 1–30 header count. On DevKitM-1, the two headers are J1 and J3; verify board orientation and continuity with power disconnected.

## 1. MQ-135 divider: rework or disconnect AO first

The written circuit has **R2 = 10 kΩ from AO to ADC, R4 = 20 kΩ from ADC to ground**:

`V_ADC = V_AO × 20 / (10 + 20)`

That is 3.333 V at 5.0 V AO and 3.50 V at 5.25 V AO, before resistor tolerance. This is poor headroom for a 3.3 V pin and can exceed the nominal supply. Do not rely on software clipping as electrical protection. The current C6 datasheet lists a 0–3.3 V calibrated range for qualifying production dates; earlier batches differ. Do not assume a C3's ADC range applies to the C6.

**Recommended change for this carrier:** use **20 kΩ top / 10 kΩ bottom** (swap the fitted values if the stated nets are correct). This gives a divider factor of 3 and about 1.67 V at 5 V AO. The shipped `MQ_DIVIDER_FACTOR` is **3.0 for that changed circuit**, not for the original one. Consider 100 nF from ADC to ground close to the ESP as in Espressif's ADC characterization; it does not replace a safe divider.

With the ESP removed/disconnected, verify which resistor connects to ground. Power only the sensor/divider from the intended controlled supply, measure AO and divider output with a meter, then power off before reconnecting. Never apply an external test voltage to an installed ESP input while its supply is off. If you cannot confirm the divider, leave AO physically disconnected and keep `ENABLE_MQ 0`. Check the ground is common and AO is not confused with the module's digital output.

The heater can consume nearly 1 W. Expect warmth; keep it well away from the DHT22 and its airflow. Winsen specifies over 48 hours of preheating under its test conditions; initial conditioning is different from each-start stabilization. The firmware's 15-minute `mq_warm` timer is only a stabilization indicator. Store raw ADC/millivolts and compare relative behavior after conditioning. Without known load resistance, reference calibration, environmental compensation and gas selectivity, do not report **CO₂ ppm**. A dedicated CO₂ sensor would be needed for credible CO₂ measurements.

## 2. PMS UART: check the onboard USB bridge conflict

Your notes assign PMS UART to GPIO16/17. On DevKitM-1, **GPIO16 is UART0 TX and GPIO17 is UART0 RX**, also connected to the onboard USB-to-UART bridge. The normal crossover would put PMS TX onto GPIO17, where the bridge's TX is also connected. Two transmitter outputs on one net can contend. Moving the USB cable to native USB does not physically disconnect that bridge pin.

**Recommended carrier-compatible workaround:** use a removable cable/header adapter to isolate the original PMS TX-to-GPIO17 net and run **PMS TX → an otherwise unused GPIO20**. Leave PMS RX disconnected; this firmware receives factory active-mode reports and sends no commands. Verify GPIO20 has no other connection on your carrier before choosing it. The shipped `PMS_RX_PIN 20` matches this workaround. Do not leave the old connection attached while adding the new one.

If you retain GPIO17, first inspect the exact DevKit revision schematic and physically isolate the bridge's TX connection from that net. Changing `Serial1` in code does not do this. Do not cut traces blindly; the jumper approach on the removable PMS cable is easier to undo. Native USB on GPIO12/13 avoids routing debug output through the PMS pins.

PMS power: 5 V and common ground; UART logic is 3.3 V. Check the sensor cable's pin numbering against its manual—wire colors are not a pinout. Ensure SET and RESET are not held low. Give the fan unobstructed intake/exhaust and wait at least 30 seconds for valid readings. This parser supports the **standard PMS5003 32-byte / length-28 protocol**. Your notes also say “PMS5003S”; inspect the actual label. If a variant uses a different frame layout, keep it disabled until its datasheet is matched. Unsupported lengths are rejected rather than interpreted as PM.

## 3. DHT and I²C boot considerations

GPIO4 **and GPIO5 are strapping pins too** (the old notes listed only 8/9/15). Their role differs from the boot-download strap; their use is not proof that the PCB is unusable. Keep the intended pull-ups, avoid adding arbitrary pull-downs, and verify repeated cold starts with peripherals attached. They are used by the C6's JTAG-related startup configuration; consult the chip's strapping table for your configuration. Do not burn eFuses to work around an unverified wiring problem.

| Function | Firmware GPIO | Check |
|---|---:|---|
| DHT22 DATA | 4 | 10 kΩ pull-up to 3.3 V; correct sensor/module pin order |
| VEML7700 SDA | 6 | Address 0x10; breakout powered from 3.3 V |
| VEML7700 SCL | 5 | Pull-ups to 3.3 V, not 5 V |
| MQ analog | 0 | Corrected divider only; disabled initially |
| PMS receive | 20 | Proposed isolated jumper rework, not your original GPIO17 trace |
| Native USB | 12/13 | Keep free; select correct USB connector |

The VEML7700 uses low gain (1/8) and 25 ms integration for bright environments. Saturation gives null, not a believable low lux reading. This trades dim-light resolution for outdoor range. Compare readings to a reference if lux accuracy matters. Protect it from rain while accounting for window transmission.

## 4. Power-on sequence and acceptance tests

1. With all power off, inspect solder bridges, connector orientation and 5 V/3.3 V/GND continuity. A low-resistance short must be resolved before power. Do not judge power capability from trace width alone.
2. Start with the ESP alone and a known-good data cable. Confirm USB enumeration and successful sketch upload. Use one supported power arrangement; avoid unintended backfeeding through multiple supplies. Espressif lists header power and USB power as mutually exclusive options.
3. Add DHT22 and VEML7700; default firmware should output finite readings every 10 seconds. Native serial runs at 115200. Check room temperature against another thermometer and RH for plausibility. Shade the temperature sensor and shield it from board/heater heat. Outdoor air temperature requires a ventilated radiation shield; direct sun creates measurement bias.
4. Verify the MQ divider separately, then connect AO and set `ENABLE_MQ 1`. Compare the firmware ADC mV with a meter. A disconnected analog input can float: the program cannot prove the sensor is connected from voltage alone.
5. Resolve PMS wiring, verify the exact model, then set `ENABLE_PMS 1`. Expect `pms_good_frames` to rise and `status.pms` to become `ok` after warmup. Many bad frames indicate wiring, noise or protocol mismatch. Disconnecting PMS should produce null after 10 seconds without valid frames.
6. Enable Wi-Fi/MQTT only after USB readings are stable. Measure the 5 V and 3.3 V rails with heater, fan and Wi-Fi all active. A properly rated regulated 5 V source and cable are needed; verify peak current and board power path. Random resets on connection often indicate supply droop.
7. Unplug/replug USB, restart the broker, turn the access point off/on, disconnect each sensor, and repeat 10 cold starts. Observe null/fault states, reconnection, and new boot IDs. Do not expect recovery of samples missed during an outage.
8. Run a 24-hour soak. Check gaps, reset count/boot IDs, sensor errors, actual timestamps and dashboard staleness. Only then deploy outdoors and collect training data.

For a bench heat-response test, use ordinary gentle ambient warming and a reference thermometer; keep heaters, flames, solvents and smoke away from the assembly. You do not need to expose gas sensors to hazardous test gases to prove the data pipeline works.

## Primary references

- Espressif board guide and pin table: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c6/esp32-c6-devkitm-1/user_guide.html
- Board schematic (check revision against your unit): https://dl.espressif.com/dl/schematics/esp32-c6-devkitm-1-schematics.pdf
- C6 datasheet, strapping and ADC characteristics: https://www.espressif.com/sites/default/files/documentation/esp32-c6_datasheet_en.pdf
- Plantower PMS5003 manual: https://cdn-shop.adafruit.com/product-files/3686/plantower-pms5003-manual_v2-3.pdf
- Winsen MQ135 specifications: https://www.winsen-sensor.com/product/mq135.html
- Adafruit VEML7700 library: https://github.com/adafruit/Adafruit_VEML7700

References checked on 3 November 2026. Measurements and your actual PCB nets take precedence over the supplied prose pin map.
