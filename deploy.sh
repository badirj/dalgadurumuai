#!/bin/bash

# Dalga Analizi Sistemi Deployment Script
# Ubuntu 20.04 VDS için

set -e

echo "=== Dalga Analizi Sistemi Deployment Başlıyor ==="

# Sistem güncellemeleri
echo "Sistem güncellemeleri yapılıyor..."
sudo apt-get update
sudo apt-get upgrade -y

# Gerekli paketlerin kurulumu
echo "Gerekli paketler kuruluyor..."
sudo apt-get install -y \
    docker.io \
    docker-compose \
    git \
    curl \
    wget \
    unzip \
    postgresql-client \
    python3 \
    python3-pip \
    python3-venv

# Docker servisini başlat
echo "Docker servisi başlatılıyor..."
sudo systemctl start docker
sudo systemctl enable docker

# Kullanıcıyı docker grubuna ekle
sudo usermod -aG docker $USER

# Proje dizinini oluştur
echo "Proje dizini oluşturuluyor..."
mkdir -p /opt/wave-analyzer
cd /opt/wave-analyzer

# .env dosyasını oluştur
echo ".env dosyası oluşturuluyor..."
cat > .env << EOF
# Flask Ayarları
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=False

# Veritabanı Ayarları
DATABASE_URL=postgresql://wave_user:wave_password@localhost:5432/wave_analyzer

# Sunucu Ayarları
HOST=0.0.0.0
PORT=5000

# Analiz Ayarları
ANALYSIS_INTERVAL=5
SAVE_FRAMES=True
FRAMES_DIR=saved_frames

# YOLO Model Ayarları
YOLO_CONFIDENCE_THRESHOLD=0.5

# ESP32-CAM Ayarları
ESP32_TIMEOUT=10
ESP32_RETRY_COUNT=3
EOF

# Docker Compose ile servisleri başlat
echo "Docker servisleri başlatılıyor..."
sudo docker-compose up -d

# Servislerin başlamasını bekle
echo "Servislerin başlaması bekleniyor..."
sleep 30

# Health check
echo "Sistem sağlık kontrolü yapılıyor..."
if curl -f http://localhost:5000/api/health; then
    echo "✅ Sistem başarıyla çalışıyor!"
else
    echo "❌ Sistem başlatılamadı!"
    exit 1
fi

# Firewall ayarları
echo "Firewall ayarları yapılıyor..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp
sudo ufw --force enable

# Systemd service dosyası oluştur
echo "Systemd service dosyası oluşturuluyor..."
sudo tee /etc/systemd/system/wave-analyzer.service > /dev/null << EOF
[Unit]
Description=Wave Analyzer System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/wave-analyzer
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Service'i etkinleştir
sudo systemctl enable wave-analyzer.service

echo "=== Deployment Tamamlandı! ==="
echo ""
echo "Sistem bilgileri:"
echo "- API URL: http://$(curl -s ifconfig.me):5000"
echo "- Health Check: http://$(curl -s ifconfig.me):5000/api/health"
echo "- Kamera Listesi: http://$(curl -s ifconfig.me):5000/api/cameras"
echo ""
echo "Yararlı komutlar:"
echo "- Servis durumu: sudo systemctl status wave-analyzer"
echo "- Logları görüntüle: sudo docker-compose logs -f"
echo "- Servisi yeniden başlat: sudo systemctl restart wave-analyzer"
echo "- Servisi durdur: sudo systemctl stop wave-analyzer"
echo ""
echo "ESP32-CAM kurulumu için:"
echo "1. ESP32-CAM'i ağa bağlayın"
echo "2. IP adresini öğrenin"
echo "3. API'ye kamera ekleyin:"
echo "   curl -X POST http://localhost:5000/api/cameras \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"camera_id\":\"test_cam\",\"name\":\"Test Kamera\",\"location\":\"Test\",\"ip_address\":\"ESP32_IP_ADRESI\"}'" 