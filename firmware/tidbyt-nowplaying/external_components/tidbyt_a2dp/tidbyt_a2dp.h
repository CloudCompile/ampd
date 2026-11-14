#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <BluetoothA2DPSource.h>
#include <deque>
#include <mutex>
#include <string>
#include "esphome/core/component.h"
#include "esphome/core/log.h"

namespace tidbyt_a2dp {

class TidbytA2DPSource : public esphome::Component {
 public:
  TidbytA2DPSource(const std::string &device_name, const std::string &url)
      : device_name_(device_name), url_(url) {}

  void setup() override;
  void loop() override {}
  float get_setup_priority() const override { return esphome::setup_priority::AFTER_WIFI; }
  void dump_config() override;

 protected:
  static TidbytA2DPSource *instance_;
  static int32_t audio_callback(uint8_t *data, int32_t bytes);
  static void stream_task(void *arg);
  void stream_loop();
  bool connect_stream(WiFiClient &client);
  int read_stream_bytes(WiFiClient &client, uint8_t *buffer, size_t capacity);

  BluetoothA2DPSource source_;
  std::string device_name_;
  std::string url_;
  std::deque<uint8_t> pcm_;
  std::mutex mutex_;
  TaskHandle_t task_{nullptr};
};

}  // namespace tidbyt_a2dp
