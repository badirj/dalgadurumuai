"""
Konfigürasyon Dosyası

Bu dosya uygulama ayarlarını içerir.
"""

import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class Config:
    """Uygulama konfigürasyonu"""
    
    # Flask ayarları
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Veritabanı ayarları
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost/wave_analyzer')
    
    # Sunucu ayarları
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Analiz ayarları
    ANALYSIS_INTERVAL = int(os.getenv('ANALYSIS_INTERVAL', 5))  # saniye
    SAVE_FRAMES = os.getenv('SAVE_FRAMES', 'True').lower() == 'true'
    FRAMES_DIR = os.getenv('FRAMES_DIR', 'saved_frames')
    
    # YOLO model ayarları
    YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH', None)  # None ise varsayılan kullanılır
    YOLO_CONFIDENCE_THRESHOLD = float(os.getenv('YOLO_CONFIDENCE_THRESHOLD', 0.5))
    
    # ESP32-CAM ayarları
    ESP32_TIMEOUT = int(os.getenv('ESP32_TIMEOUT', 10))  # saniye
    ESP32_RETRY_COUNT = int(os.getenv('ESP32_RETRY_COUNT', 3))
    
    # Örnek kamera ayarları (test için)
    SAMPLE_CAMERAS = [
        {
            'camera_id': 'karasu_1',
            'name': 'Karasu Sahil Kamerası',
            'location': 'Karasu',
            'ip_address': '192.168.1.100',
            'port': 80,
            'description': 'Karasu sahilinde deniz manzarası'
        },
        {
            'camera_id': 'sakarya_1',
            'name': 'Sakarya Merkez Kamerası',
            'location': 'Sakarya',
            'ip_address': '192.168.1.101',
            'port': 80,
            'description': 'Sakarya merkezde deniz manzarası'
        },
        {
            'camera_id': 'florya_1',
            'name': 'Florya Sahil Kamerası',
            'location': 'Florya',
            'ip_address': '192.168.1.102',
            'port': 80,
            'description': 'Florya sahilinde deniz manzarası'
        }
    ]
    
    # Lokasyon bilgileri
    LOCATIONS = [
        {
            'id': 'karasu',
            'name': 'Karasu',
            'description': 'Sakarya\'nın Karasu ilçesi sahil şeridi',
            'coordinates': {'lat': 41.0975, 'lng': 30.6908}
        },
        {
            'id': 'sakarya',
            'name': 'Sakarya',
            'description': 'Sakarya merkez sahil şeridi',
            'coordinates': {'lat': 40.7569, 'lng': 30.3781}
        },
        {
            'id': 'florya',
            'name': 'Florya',
            'description': 'İstanbul Florya sahil şeridi',
            'coordinates': {'lat': 40.9769, 'lng': 28.7972}
        }
    ]
    
    # Dalga yoğunluk seviyeleri
    WAVE_INTENSITY_LEVELS = [
        {
            'level': 0,
            'name': 'Sakin',
            'description': 'Deniz çok sakin, dalga yok',
            'color': '#00ff00',
            'safety': 'Güvenli'
        },
        {
            'level': 1,
            'name': 'Hafif Dalgalı',
            'description': 'Hafif dalgalar var, güvenli',
            'color': '#90EE90',
            'safety': 'Güvenli'
        },
        {
            'level': 2,
            'name': 'Orta Dalgalı',
            'description': 'Orta şiddette dalgalar, dikkatli olun',
            'color': '#FFFF00',
            'safety': 'Dikkatli'
        },
        {
            'level': 3,
            'name': 'Dalgalı',
            'description': 'Güçlü dalgalar, dikkat gerekli',
            'color': '#FFA500',
            'safety': 'Dikkat'
        },
        {
            'level': 4,
            'name': 'Çok Dalgalı',
            'description': 'Çok güçlü dalgalar, tehlikeli',
            'color': '#FF0000',
            'safety': 'Tehlikeli'
        }
    ]
    
    # Kalabalık seviyeleri
    CROWD_LEVELS = [
        {
            'level': 'Boş',
            'description': 'Hiç kimse görünmüyor, güvenli',
            'color': '#00ff00',
            'max_people': 0
        },
        {
            'level': 'Az Kalabalık',
            'description': 'Az sayıda insan var, rahat',
            'color': '#90EE90',
            'max_people': 5
        },
        {
            'level': 'Orta Kalabalık',
            'description': 'Normal kalabalık seviyesi',
            'color': '#FFFF00',
            'max_people': 15
        },
        {
            'level': 'Kalabalık',
            'description': 'Kalabalık, dikkatli olun',
            'color': '#FFA500',
            'max_people': 30
        },
        {
            'level': 'Çok Kalabalık',
            'description': 'Çok kalabalık, yoğun',
            'color': '#FF0000',
            'max_people': 999
        }
    ]


# Konfigürasyon örneği
config = Config() 