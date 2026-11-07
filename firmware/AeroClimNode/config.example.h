#pragma once
// Start over native USB with PMS and MQ AO physically disconnected.
#define ENABLE_WIFI 0
#define ENABLE_PMS 0       // Set 1 ONLY after reading docs/HARDWARE.md
#define ENABLE_MQ 0        // Software disabling does NOT protect a connected ADC
#define WIFI_SSID "YOUR_2_4_GHZ_WIFI"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define MQTT_HOST "192.168.1.100" // PC LAN IPv4; never 127.0.0.1 here
#define MQTT_PORT 1883
#define MQTT_USER ""
#define MQTT_PASSWORD ""
#define MQTT_TLS 0
// If TLS=1, replace with the broker's issuing CA PEM; no insecure bypass.
static const char MQTT_CA[] = "";
#define TOPIC_ROOT "aeroclim/lab"
#define NODE_ID "node4"
#define DHT_PIN 4
#define I2C_SDA 6
#define I2C_SCL 5
// Recommended flying-wire rework: PMS TX -> free GPIO20; PMS RX left unconnected.
// Verify GPIO20 is unused on YOUR carrier. Isolate original TX->GPIO17 connection.
#define PMS_RX_PIN 20
#define MQ_PIN 0
// After rework: Rtop=20k from AO to ADC; Rbottom=10k ADC to ground.
#define MQ_DIVIDER_FACTOR 3.0f
#define MQ_WARMUP_MS 900000UL // stabilization indication, not initial 48h conditioning
#define SAMPLE_MS 10000UL
#define EDGE_MS 900000UL
#define PMS_WARMUP_MS 30000UL
