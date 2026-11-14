#include "tidbyt_a2dp.h"

#include <WiFi.h>
#include <cstring>

namespace tidbyt_a2dp {

TidbytA2DPSource *TidbytA2DPSource::instance_ = nullptr;

void TidbytA2DPSource::setup() {
  instance_ = this;
  source_.set_data_callback(TidbytA2DPSource::audio_callback);
  // Do not read the library's saved connected_bda NVS namespace during
  // first pairing. The Tidbyt factory image has no prior A2DP peer record;
  // the library's current auto-reconnect path logs NVS OPEN ERROR and then
  // hits a null queue delete. Scan/connect-by-name is the safe bootstrap.
  source_.set_auto_reconnect(false);
  source_.start(device_name_.c_str());
  xTaskCreatePinnedToCore(TidbytA2DPSource::stream_task, "tidbyt_pcm",
                          8192, this, 1, &task_, 0);
}

void TidbytA2DPSource::dump_config() {
  ESP_LOGCONFIG("tidbyt_a2dp", "Bluetooth A2DP source:");
  ESP_LOGCONFIG("tidbyt_a2dp", "  Target: %s", device_name_.c_str());
  ESP_LOGCONFIG("tidbyt_a2dp", "  PCM: 44.1kHz signed 16-bit stereo");
}

int32_t TidbytA2DPSource::audio_callback(uint8_t *data, int32_t bytes) {
  auto *self = instance_;
  if (!self) {
    memset(data, 0, bytes);
    return bytes;
  }
  std::lock_guard<std::mutex> lock(self->mutex_);
  int32_t n = 0;
  while (n < bytes && !self->pcm_.empty()) {
    data[n++] = self->pcm_.front();
    self->pcm_.pop_front();
  }
  if (n < bytes) memset(data + n, 0, bytes - n);
  return bytes;
}

void TidbytA2DPSource::stream_task(void *arg) {
  static_cast<TidbytA2DPSource *>(arg)->stream_loop();
}

bool TidbytA2DPSource::connect_stream(WiFiClient &client) {
  // v1 is deliberately plain HTTP: the Tidbyt cannot afford TLS beside
  // the HUB75 DMA framebuffer. The Caddy relay authenticates the scoped key.
  String u(url_.c_str());
  int scheme = u.indexOf("://");
  int start = scheme >= 0 ? scheme + 3 : 0;
  int slash = u.indexOf('/', start);
  String hostport = slash >= 0 ? u.substring(start, slash) : u.substring(start);
  String path = slash >= 0 ? u.substring(slash) : "/";
  int colon = hostport.indexOf(':');
  String host = colon >= 0 ? hostport.substring(0, colon) : hostport;
  uint16_t port = colon >= 0 ? (uint16_t) hostport.substring(colon + 1).toInt() : 80;
  if (!client.connect(host.c_str(), port)) return false;
  client.printf("GET %s HTTP/1.1\r\nHost: %s\r\nConnection: keep-alive\r\n\r\n",
                path.c_str(), host.c_str());
  String line = client.readStringUntil('\n');
  if (line.indexOf(" 200 ") < 0) {
    client.stop();
    return false;
  }
  bool chunked = false;
  while (client.connected()) {
    line = client.readStringUntil('\n');
    if (line == "\r" || line.length() == 0) break;
    line.toLowerCase();
    if (line.startsWith("transfer-encoding:") && line.indexOf("chunked") >= 0)
      chunked = true;
  }
  chunked_ = chunked;
  chunk_remaining_ = 0;
  return true;
}

int TidbytA2DPSource::read_stream_bytes(WiFiClient &client, uint8_t *buffer,
                                       size_t capacity) {
  if (!chunked_) return client.read(buffer, capacity);
  if (chunk_remaining_ == 0) {
    String size_line = client.readStringUntil('\n');
    size_line.trim();
    int semi = size_line.indexOf(';');
    if (semi >= 0) size_line.remove(semi);
    chunk_remaining_ = strtoul(size_line.c_str(), nullptr, 16);
    if (chunk_remaining_ == 0) return -1;
  }
  size_t want = std::min(capacity, chunk_remaining_);
  int got = client.read(buffer, want);
  if (got > 0) chunk_remaining_ -= (size_t)got;
  if (chunk_remaining_ == 0) {
    (void)client.readStringUntil('\n');  // consume CRLF after chunk data
  }
  return got;
}

void TidbytA2DPSource::stream_loop() {
  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      vTaskDelay(pdMS_TO_TICKS(1000));
      continue;
    }
    WiFiClient client;
    if (!connect_stream(client)) {
      vTaskDelay(pdMS_TO_TICKS(2000));
      continue;
    }
    uint8_t buf[1460];
    while (client.connected()) {
      int n = read_stream_bytes(client, buf, sizeof(buf));
      if (n <= 0) {
        vTaskDelay(pdMS_TO_TICKS(5));
        continue;
      }
      std::lock_guard<std::mutex> lock(mutex_);
      // 128 KiB ≈ 370ms of PCM: enough to bridge WiFi jitter without
      // letting a stalled Bose connection consume the whole heap.
      while (pcm_.size() + (size_t)n > 131072) pcm_.pop_front();
      pcm_.insert(pcm_.end(), buf, buf + n);
    }
    client.stop();
  }
}

}  // namespace tidbyt_a2dp
