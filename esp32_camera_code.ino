/*
  ESP32-CAM Dalga Analizi Sistemi
  Bu kod ESP32-CAM'i WiFi ağına bağlar ve HTTP stream/snapshot sağlar
*/

#include "esp_camera.h"
#include <WiFi.h>
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include "fb_gfx.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h"

// WiFi ayarları
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// ESP32-CAM pin tanımlamaları
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    22
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     33

// HTTP server
esp_err_t status_led_handler(httpd_req_t *req);
esp_err_t index_handler(httpd_req_t *req);
esp_err_t capture_handler(httpd_req_t *req);
esp_err_t stream_handler(httpd_req_t *req);
esp_err_t cmd_handler(httpd_req_t *req);

static const char* PROGMEM INDEX_HTML = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <title>ESP32-CAM Dalga Analizi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; text-align: center; margin:0px auto; padding-top: 30px;}
        img { width: auto; max-width: 100%; height: auto; }
        .button { background-color: #4CAF50; border: none; color: white; padding: 15px 32px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; cursor: pointer; }
        .button2 { background-color: #f44336; }
        .container { margin: 20px; }
    </style>
</head>
<body>
    <h1>ESP32-CAM Dalga Analizi</h1>
    <div class="container">
        <p><a href="/capture"><button class="button">Fotoğraf Çek</button></a></p>
        <p><a href="/stream"><button class="button">Canlı Yayın</button></a></p>
        <p><a href="/"><button class="button">Ana Sayfa</button></a></p>
    </div>
    <div class="container">
        <img id="stream" src="" style="display:none;">
        <img id="capture" src="" style="display:none;">
    </div>
    <script>
        var baseHost = document.location.origin;
        var streamUrl = baseHost + ':81/stream';
        var captureUrl = baseHost + '/capture';
        
        function showStream() {
            document.getElementById('stream').style.display = 'block';
            document.getElementById('capture').style.display = 'none';
            document.getElementById('stream').src = streamUrl;
        }
        
        function showCapture() {
            document.getElementById('capture').style.display = 'block';
            document.getElementById('stream').style.display = 'none';
            document.getElementById('capture').src = captureUrl + '?t=' + new Date().getTime();
        }
        
        // URL parametrelerini kontrol et
        if (window.location.pathname === '/stream') {
            showStream();
        } else if (window.location.pathname === '/capture') {
            showCapture();
        }
    </script>
</body>
</html>
)rawliteral";

void startCameraServer();

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // ESP32-CAM ayarları
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // PSRAM varsa kullan
  if(psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Kamera başlat
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Kamera başlatılamadı: 0x%x", err);
    return;
  }

  // Kamera ayarları
  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);     // -2 to 2
  s->set_contrast(s, 0);       // -2 to 2
  s->set_saturation(s, 0);     // -2 to 2
  s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
  s->set_whitebal(s, 1);       // 0 = disable , 1 = enable
  s->set_awb_gain(s, 1);       // 0 = disable , 1 = enable
  s->set_wb_mode(s, 0);        // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
  s->set_exposure_ctrl(s, 1);  // 0 = disable , 1 = enable
  s->set_aec2(s, 0);          // 0 = disable , 1 = enable
  s->set_gain_ctrl(s, 1);      // 0 = disable , 1 = enable
  s->set_agc_gain(s, 0);       // 0 to 30
  s->set_gainceiling(s, (gainceiling_t)0);  // 0 to 6
  s->set_bpc(s, 0);           // 0 = disable , 1 = enable
  s->set_wpc(s, 1);           // 0 = disable , 1 = enable
  s->set_raw_gma(s, 1);       // 0 = disable , 1 = enable
  s->set_lenc(s, 1);          // 0 = disable , 1 = enable
  s->set_hmirror(s, 0);       // 0 = disable , 1 = enable
  s->set_vflip(s, 0);         // 0 = disable , 1 = enable
  s->set_dcw(s, 1);           // 0 = disable , 1 = enable
  s->set_colorbar(s, 0);      // 0 = disable , 1 = enable

  // WiFi bağlantısı
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi bağlandı");

  startCameraServer();

  Serial.print("Kamera hazır! IP adresi: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  delay(1);
}

// HTTP server başlat
void startCameraServer(){
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  httpd_uri_t index_uri = {
    .uri       = "/",
    .method    = HTTP_GET,
    .handler   = index_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t capture_uri = {
    .uri       = "/capture",
    .method    = HTTP_GET,
    .handler   = capture_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };

  httpd_uri_t cmd_uri = {
    .uri       = "/control",
    .method    = HTTP_GET,
    .handler   = cmd_handler,
    .user_ctx  = NULL
  };

  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &index_uri);
    httpd_register_uri_handler(camera_httpd, &capture_uri);
    httpd_register_uri_handler(camera_httpd, &cmd_uri);
  }

  config.server_port += 1;
  config.ctrl_port += 1;
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}

// Ana sayfa handler
esp_err_t index_handler(httpd_req_t *req){
  httpd_resp_set_type(req, "text/html");
  return httpd_resp_send(req, (const char *)INDEX_HTML, strlen(INDEX_HTML));
}

// Fotoğraf çekme handler
esp_err_t capture_handler(httpd_req_t *req){
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  int64_t fr_start = 0;
  int64_t fr_end = 0;

  fr_start = esp_timer_get_time();
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Kamera capture başarısız");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  fr_end = esp_timer_get_time();
  Serial.printf("JPG: %uB %ums", (uint32_t)(fb->len), (uint32_t)((fr_end - fr_start)/1000));
  
  res = httpd_resp_set_type(req, "image/jpeg");
  if(res == ESP_OK){
    res = httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  }

  if(res == ESP_OK){
    size_t fb_len = 0;
    if(fb->format == PIXFORMAT_JPEG){
      fb_len = fb->len;
      res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
    } else {
      jpg_chunking_t jchunk = {req, 0};
      res = frame2jpg_cb(fb, 80, jpg_encode_stream, &jchunk)?ESP_OK:ESP_FAIL;
      httpd_resp_send_chunk(req, NULL, 0);
      fb_len = jchunk.len;
    }
    esp_camera_fb_return(fb);
    int64_t fr_end = esp_timer_get_time();
    Serial.printf("JPG: %uB %ums", (uint32_t)(fb_len), (uint32_t)((fr_end - fr_start)/1000));
    return res;
  }
  esp_camera_fb_return(fb);
  Serial.printf("Capture başarısız");
  return res;
}

// Stream handler
esp_err_t stream_handler(httpd_req_t *req){
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[64];

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if(res != ESP_OK){
    return res;
  }

  while(true){
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Kamera capture başarısız");
      res = ESP_FAIL;
    } else {
      if(fb->format != PIXFORMAT_JPEG){
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if(!jpeg_converted){
          Serial.println("JPEG conversion başarısız");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)part_buf[0], hlen);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if(res != ESP_OK){
      break;
    }
  }
  return res;
}

// Komut handler
esp_err_t cmd_handler(httpd_req_t *req){
  char*  buf;
  size_t buf_len;
  char variable[32] = {0,};
  char value[32] = {0,};

  buf_len = httpd_req_get_url_query_len(req) + 1;
  if (buf_len > 1) {
    buf = (char*)malloc(buf_len);
    if(!buf){
      httpd_resp_send_500(req);
      return ESP_FAIL;
    }
    if (httpd_req_get_url_query_str(req, buf, buf_len) == ESP_OK) {
      if (httpd_query_key_value(buf, "var", variable, sizeof(variable)) == ESP_OK &&
          httpd_query_key_value(buf, "val", value, sizeof(value)) == ESP_OK) {
      } else {
        free(buf);
        httpd_resp_send_404(req);
        return ESP_FAIL;
      }
    } else {
      free(buf);
      httpd_resp_send_404(req);
      return ESP_FAIL;
    }
    free(buf);
  } else {
    httpd_resp_send_404(req);
    return ESP_FAIL;
  }

  int val = atoi(value);
  sensor_t * s = esp_camera_sensor_get();
  int res = 0;

  if(!strcmp(variable, "framesize")) {
    if(s->pixformat == PIXFORMAT_JPEG) res = s->set_framesize(s, (framesize_t)val);
  }
  else if(!strcmp(variable, "quality")) res = s->set_quality(s, val);
  else if(!strcmp(variable, "contrast")) res = s->set_contrast(s, val);
  else if(!strcmp(variable, "brightness")) res = s->set_brightness(s, val);
  else if(!strcmp(variable, "saturation")) res = s->set_saturation(s, val);
  else if(!strcmp(variable, "gainceiling")) res = s->set_gainceiling(s, (gainceiling_t)val);
  else if(!strcmp(variable, "colorbar")) res = s->set_colorbar(s, val);
  else if(!strcmp(variable, "awb")) res = s->set_whitebal(s, val);
  else if(!strcmp(variable, "agc")) res = s->set_gain_ctrl(s, val);
  else if(!strcmp(variable, "aec")) res = s->set_exposure_ctrl(s, val);
  else if(!strcmp(variable, "hmirror")) res = s->set_hmirror(s, val);
  else if(!strcmp(variable, "vflip")) res = s->set_vflip(s, val);
  else if(!strcmp(variable, "awb_gain")) res = s->set_awb_gain(s, val);
  else if(!strcmp(variable, "agc_gain")) res = s->set_agc_gain(s, val);
  else if(!strcmp(variable, "aec_value")) res = s->set_aec_value(s, val);
  else if(!strcmp(variable, "aec2")) res = s->set_aec2(s, val);
  else if(!strcmp(variable, "dcw")) res = s->set_dcw(s, val);
  else if(!strcmp(variable, "bpc")) res = s->set_bpc(s, val);
  else if(!strcmp(variable, "wpc")) res = s->set_wpc(s, val);
  else if(!strcmp(variable, "raw_gma")) res = s->set_raw_gma(s, val);
  else if(!strcmp(variable, "lenc")) res = s->set_lenc(s, val);
  else if(!strcmp(variable, "wb_mode")) res = s->set_wb_mode(s, val);
  else if(!strcmp(variable, "ae_level")) res = s->set_ae_level(s, val);
  else {
      res = -1;
  }

  if(res){
    return httpd_resp_send_500(req);
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, NULL, 0);
}

static esp_err_t stream_handler(httpd_req_t *req){
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[64];

  static int64_t last_frame = 0;
  if(!last_frame) {
    last_frame = esp_timer_get_time();
  }

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if(res != ESP_OK){
    return res;
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while(true){
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Kamera capture başarısız");
      res = ESP_FAIL;
    } else {
      if(fb->format != PIXFORMAT_JPEG){
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if(!jpeg_converted){
          Serial.println("JPEG conversion başarısız");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }
    if(res == ESP_OK){
      size_t hlen = snprintf((char *)part_buf[0], 64, _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf[0], hlen);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if(res != ESP_OK){
      break;
    }
    int64_t fr_end = esp_timer_get_time();
    int64_t frame_time = fr_end - last_frame;
    last_frame = fr_end;
    frame_time /= 1000;
    uint32_t avg_frame_time = ra_filter_run(&ra_filter, frame_time);
    Serial.printf("MJPG: %uB %ums (%.1ffps)\n",
        (uint32_t)(_jpg_buf_len),
        (uint32_t)frame_time, 1000000.0 / (uint32_t)avg_frame_time
    );
  }

  last_frame = 0;
  return res;
}

// Stream için gerekli değişkenler
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;
httpd_handle_t camera_httpd = NULL;

// Frame rate filter
static ra_filter_t ra_filter;
static ra_filter_t * ra_filter_init(ra_filter_t * filter, size_t sample_size){
    memset(filter, 0, sizeof(ra_filter_t));

    filter->values = (int *)malloc(sample_size * sizeof(int));
    if(!filter->values){
        return NULL;
    }
    memset(filter->values, 0, sample_size * sizeof(int));

    filter->size = sample_size;
    return filter;
}

static int ra_filter_run(ra_filter_t * filter, int value){
    if(!filter->values){
        return value;
    }
    filter->sum -= filter->values[filter->index];
    filter->values[filter->index] = value;
    filter->sum += filter->values[filter->index];
    filter->index++;
    filter->index = filter->index % filter->size;
    if (filter->count < filter->size) {
        filter->count++;
    }
    return filter->sum / filter->count;
} 