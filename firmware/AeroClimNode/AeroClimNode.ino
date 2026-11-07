// AeroClim v3 — Arduino ESP32 core 3.x, ESP32C6 Dev Module, native USB CDC.
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_VEML7700.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <time.h>
#include "config.h"
#include "core.h"
#if !ARDUINO_USB_CDC_ON_BOOT
#error "Enable USB CDC On Boot; use the native ESP32 USB port, not UART bridge."
#endif
static_assert(SAMPLE_MS>=2500UL,"DHT22 requires slow sampling");
DHT dht(DHT_PIN,DHT22);
Adafruit_VEML7700 light;
HardwareSerial dust(1);
#if MQTT_TLS
WiFiClientSecure transport;
#else
WiFiClient transport;
#endif
PubSubClient mqtt(transport);
PMSParser pms;
Holt holt;
bool lightOK=false,edge=false;
uint32_t lastSample=0,lastFrame=0,lastEdge=0,lastWiFi=0,lastMqtt=0;
uint32_t seq=0,mqttFailures=0;
float edgeSum=0;
uint32_t edgeN=0;
char bootId[18],topic[128],statusTopic[128],clientId[96];

bool probeLight(){
  Wire.beginTransmission(0x10);
  return Wire.endTransmission()==0;
}
void initLight(){
  lightOK=light.begin(&Wire);
  if(lightOK){
    light.setGain(VEML7700_GAIN_1_8);
    light.setIntegrationTime(VEML7700_IT_25MS);
  }
}
void connectNetwork(uint32_t now){
#if ENABLE_WIFI
  if(WiFi.status()!=WL_CONNECTED){
    if(uint32_t(now-lastWiFi)>=15000UL){lastWiFi=now;WiFi.disconnect();WiFi.begin(WIFI_SSID,WIFI_PASSWORD);}
    return;
  }
  if(!mqtt.connected() && uint32_t(now-lastMqtt)>=10000UL){
    lastMqtt=now;
#if MQTT_TLS
    if(time(nullptr)<1700000000 || strlen(MQTT_CA)<64) return;
#endif
    if(mqtt.connect(clientId,MQTT_USER,MQTT_PASSWORD,statusTopic,1,true,"offline"))
      mqtt.publish(statusTopic,"online",true);
    else ++mqttFailures;
  }
  mqtt.loop();
#endif
}
void sample(uint32_t now){
  JsonDocument doc;
  doc["schema"]=3; doc["source"]="hardware";
  doc["node_id"]=NODE_ID; doc["boot_id"]=bootId; doc["seq"]=seq++;
  time_t epoch=time(nullptr);
  if(epoch>=1700000000) doc["timestamp"]=(int64_t)epoch;
  else doc["timestamp"]=nullptr;
  doc["uptime_s"]=(uint64_t)(esp_timer_get_time()/1000000LL);
  float rh=dht.readHumidity(),temp=dht.readTemperature();
  bool dhtOK=isfinite(rh)&&isfinite(temp)&&rh>=0&&rh<=100&&temp>=-40&&temp<=80;
  if(dhtOK){doc["temperature_c"]=temp;doc["humidity"]=rh;edgeSum+=temp;++edgeN;}
  else{doc["temperature_c"]=nullptr;doc["humidity"]=nullptr;}
  doc["status"]["dht"]=dhtOK?"ok":"read_failed";
  if(uint32_t(now-lastEdge)>=EDGE_MS){
    if(edgeN>=EDGE_MS/SAMPLE_MS*2/3) edge=holt.update(edgeSum/edgeN);
    else{holt=Holt();edge=false;}
    edgeSum=0;edgeN=0;lastEdge=now;
  }
  doc["edge_anomaly"]=edge?1:0;
  doc["edge_samples"]=holt.n;
  if(!lightOK) initLight();
  if(lightOK && probeLight()){
    uint16_t raw=light.readALS();
    float lux=light.readLux(VEML_LUX_CORRECTED);
    if(raw<65000 && isfinite(lux)&&lux>=0&&lux<=250000){
      doc["lux"]=lux;doc["status"]["light"]="ok";
    }else{doc["lux"]=nullptr;doc["status"]["light"]="saturated_or_invalid";}
  }else{lightOK=false;doc["lux"]=nullptr;doc["status"]["light"]="missing";}
#if ENABLE_PMS
  bool warming=(esp_timer_get_time()/1000LL)<PMS_WARMUP_MS;
  bool pmOK=!warming && pms.good>0 && uint32_t(now-lastFrame)<10000UL;
  if(pmOK){doc["pm1_ugm3"]=pms.pm1;doc["pm25_ugm3"]=pms.pm25;doc["pm10_ugm3"]=pms.pm10;}
  else{doc["pm1_ugm3"]=nullptr;doc["pm25_ugm3"]=nullptr;doc["pm10_ugm3"]=nullptr;}
  doc["status"]["pms"]=pmOK?"ok":(warming?"warming":"no_valid_frame");
#else
  doc["pm1_ugm3"]=nullptr;doc["pm25_ugm3"]=nullptr;doc["pm10_ugm3"]=nullptr;
  doc["status"]["pms"]="disabled_check_wiring";
#endif
#if ENABLE_MQ
  uint32_t mv=0,raw=0;
  for(int i=0;i<16;++i){mv+=analogReadMilliVolts(MQ_PIN);raw+=analogRead(MQ_PIN);}
  mv/=16;raw/=16;
  bool clipped=raw>=4080 || mv>=3200 || mv*MQ_DIVIDER_FACTOR>5600;
  doc["mq_adc_raw"]=raw;
  if(!clipped){doc["mq_adc_mv"]=mv;doc["mq_ao_mv"]=mv*MQ_DIVIDER_FACTOR;}
  else{doc["mq_adc_mv"]=nullptr;doc["mq_ao_mv"]=nullptr;}
  doc["mq_warm"]=(esp_timer_get_time()/1000LL)>=MQ_WARMUP_MS;
  doc["status"]["mq"]=clipped?"adc_clipped":"uncalibrated_voltage";
#else
  doc["mq_adc_mv"]=nullptr;doc["mq_ao_mv"]=nullptr;doc["mq_warm"]=false;
  doc["status"]["mq"]="disabled_check_divider";
#endif
  doc["reset_reason"]=(int)esp_reset_reason();
  doc["pms_good_frames"]=pms.good;doc["pms_bad_frames"]=pms.bad;
  doc["mqtt_failures"]=mqttFailures;doc["free_heap"]=ESP.getFreeHeap();
  if(WiFi.status()==WL_CONNECTED) doc["rssi_dbm"]=WiFi.RSSI();
  else doc["rssi_dbm"]=nullptr;
  char payload[2048];
  size_t needed=measureJson(doc);
  if(needed>=sizeof(payload)){Serial.println("# ERROR payload too large");return;}
  size_t n=serializeJson(doc,payload,sizeof(payload));
  // Always observable over native USB, including during Wi-Fi/MQTT failure.
  Serial.println(payload);
  // QoS0 best effort; no misleading claim of durable delivery. seq exposes loss.
  if(mqtt.connected() && !mqtt.publish(topic,(const uint8_t*)payload,n,false)) ++mqttFailures;
}
void setup(){
  Serial.begin(115200); // no blocking while(!Serial): operates without a PC
  snprintf(bootId,sizeof(bootId),"%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random());
  snprintf(topic,sizeof(topic),"%s/%s/telemetry",TOPIC_ROOT,NODE_ID);
  snprintf(statusTopic,sizeof(statusTopic),"%s/%s/status",TOPIC_ROOT,NODE_ID);
  snprintf(clientId,sizeof(clientId),"aero-%s-%s",NODE_ID,bootId);
  dht.begin(); Wire.begin(I2C_SDA,I2C_SCL); Wire.setTimeOut(50);initLight();
#if ENABLE_PMS
  dust.setRxBufferSize(2048);
  // RX only. No PMS commands; PMS must be in factory active mode.
  dust.begin(9600,SERIAL_8N1,PMS_RX_PIN,-1);
#endif
#if ENABLE_MQ
  analogReadResolution(12); analogSetPinAttenuation(MQ_PIN,ADC_11db);
#endif
#if ENABLE_WIFI
  WiFi.mode(WIFI_STA);WiFi.setAutoReconnect(true);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  configTime(0,0,"pool.ntp.org","time.google.com");
#if MQTT_TLS
  transport.setCACert(MQTT_CA);
#endif
  transport.setTimeout(2000);
  mqtt.setServer(MQTT_HOST,MQTT_PORT);mqtt.setBufferSize(2304);mqtt.setSocketTimeout(2);
  mqtt.setKeepAlive(30);
#endif
  Serial.println("# AeroClim v3; native USB JSON every 10s; see docs/HARDWARE.md");
}
void loop(){
  uint32_t now=millis();
#if ENABLE_PMS
  while(dust.available()) if(pms.feed((uint8_t)dust.read())) lastFrame=millis();
#endif
  if(uint32_t(now-lastSample)>=SAMPLE_MS){lastSample=now;sample(now);}
  connectNetwork(now);
  delay(2);
}
