"""
Flask REST API

Bu modül mobil uygulama için REST API endpoint'lerini sağlar.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import cv2
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List

from analysis_engine import analysis_engine
from database import db_manager, Camera, CameraRequest
from wave_analyzer import WaveIntensityAnalyzer
from people_detector import PeopleDetector

app = Flask(__name__)
CORS(app)  # CORS desteği ekle

# Analiz modülleri
wave_analyzer = WaveIntensityAnalyzer()
people_detector = PeopleDetector()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Sistem sağlık kontrolü"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })


# Kamera yönetimi endpoint'leri
@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Tüm kameraları listele"""
    try:
        cameras = db_manager.get_all_cameras()
        camera_list = []
        
        for camera in cameras:
            camera_data = camera.to_dict()
            # Kamera durumunu ekle
            status = analysis_engine.get_camera_status(camera.camera_id)
            camera_data['status'] = status
            
            # En son analiz sonucunu ekle
            latest_result = analysis_engine.get_latest_result(camera.camera_id)
            camera_data['latest_analysis'] = latest_result
            
            camera_list.append(camera_data)
        
        return jsonify({
            'status': 'success',
            'cameras': camera_list,
            'count': len(camera_list)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/cameras/<camera_id>', methods=['GET'])
def get_camera(camera_id):
    """Belirli bir kameranın bilgilerini getir"""
    try:
        camera = db_manager.get_camera(camera_id)
        if not camera:
            return jsonify({
                'status': 'error',
                'message': 'Kamera bulunamadı'
            }), 404
        
        camera_data = camera.to_dict()
        status = analysis_engine.get_camera_status(camera_id)
        camera_data['status'] = status
        
        return jsonify({
            'status': 'success',
            'camera': camera_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/cameras', methods=['POST'])
def add_camera():
    """Yeni kamera ekle"""
    try:
        data = request.get_json()
        
        required_fields = ['camera_id', 'name', 'location', 'ip_address']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Eksik alan: {field}'
                }), 400
        
        # Kamerayı veritabanına ekle
        camera = db_manager.add_camera(data)
        if not camera:
            return jsonify({
                'status': 'error',
                'message': 'Kamera eklenemedi'
            }), 500
        
        # Analiz motoruna ekle
        success = analysis_engine.add_camera(
            data['camera_id'],
            data['ip_address'],
            data.get('port', 80),
            data.get('username'),
            data.get('password')
        )
        
        if not success:
            return jsonify({
                'status': 'warning',
                'message': 'Kamera eklendi ama bağlantı kurulamadı',
                'camera': camera.to_dict()
            })
        
        return jsonify({
            'status': 'success',
            'message': 'Kamera başarıyla eklendi',
            'camera': camera.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Analiz endpoint'leri
@app.route('/api/cameras/<camera_id>/start', methods=['POST'])
def start_analysis(camera_id):
    """Kamera analizini başlat"""
    try:
        success = analysis_engine.start_analysis(camera_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Kamera {camera_id} analizi başlatıldı'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Kamera {camera_id} analizi başlatılamadı'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/cameras/<camera_id>/stop', methods=['POST'])
def stop_analysis(camera_id):
    """Kamera analizini durdur"""
    try:
        analysis_engine.stop_analysis(camera_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Kamera {camera_id} analizi durduruldu'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/cameras/<camera_id>/analysis', methods=['GET'])
def get_latest_analysis(camera_id):
    """Kameranın en son analiz sonucunu getir"""
    try:
        result = analysis_engine.get_latest_result(camera_id)
        
        if result:
            return jsonify({
                'status': 'success',
                'analysis': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Analiz sonucu bulunamadı'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/cameras/<camera_id>/history', methods=['GET'])
def get_analysis_history(camera_id):
    """Kameranın analiz geçmişini getir"""
    try:
        limit = request.args.get('limit', 100, type=int)
        history = analysis_engine.get_analysis_history(camera_id, limit)
        
        return jsonify({
            'status': 'success',
            'history': history,
            'count': len(history)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Canlı analiz endpoint'i
@app.route('/api/analyze', methods=['POST'])
def analyze_image():
    """Gönderilen görüntüyü analiz et"""
    try:
        if 'image' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Görüntü dosyası bulunamadı'
            }), 400
        
        file = request.files['image']
        
        # Görüntüyü oku
        image_array = np.frombuffer(file.read(), dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({
                'status': 'error',
                'message': 'Görüntü okunamadı'
            }), 400
        
        # Analiz yap
        start_time = datetime.utcnow()
        
        wave_result = wave_analyzer.analyze_wave_intensity(image)
        people_result = people_detector.detect_people(image)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        result = {
            'timestamp': datetime.utcnow().isoformat(),
            'wave_analysis': wave_result,
            'people_analysis': people_result,
            'processing_time': processing_time,
            'image_shape': image.shape
        }
        
        return jsonify({
            'status': 'success',
            'analysis': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Kamera kayıt başvurusu endpoint'leri
@app.route('/api/requests', methods=['POST'])
def submit_camera_request():
    """Kamera kayıt başvurusu gönder"""
    try:
        data = request.get_json()
        
        required_fields = ['requester_name', 'requester_email', 'location_name', 
                          'location_address', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Eksik alan: {field}'
                }), 400
        
        # Başvuruyu kaydet
        request_obj = db_manager.add_camera_request(data)
        
        if request_obj:
            return jsonify({
                'status': 'success',
                'message': 'Başvurunuz başarıyla gönderildi',
                'request_id': request_obj.id
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Başvuru kaydedilemedi'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/requests', methods=['GET'])
def get_pending_requests():
    """Bekleyen başvuruları getir (admin)"""
    try:
        requests = db_manager.get_pending_requests()
        request_list = [req.to_dict() for req in requests]
        
        return jsonify({
            'status': 'success',
            'requests': request_list,
            'count': len(request_list)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/requests/<int:request_id>/status', methods=['PUT'])
def update_request_status(request_id):
    """Başvuru durumunu güncelle (admin)"""
    try:
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Durum belirtilmedi'
            }), 400
        
        success = db_manager.update_request_status(
            request_id, 
            data['status'], 
            data.get('admin_notes')
        )
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Başvuru durumu güncellendi'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Başvuru bulunamadı'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# İstatistik endpoint'leri
@app.route('/api/stats', methods=['GET'])
def get_system_stats():
    """Sistem istatistiklerini getir"""
    try:
        cameras = db_manager.get_all_cameras()
        
        # Aktif kamera sayısı
        active_cameras = sum(1 for cam in cameras if cam.is_active)
        
        # Analiz eden kamera sayısı
        analyzing_cameras = 0
        for camera in cameras:
            status = analysis_engine.get_camera_status(camera.camera_id)
            if status.get('analyzing', False):
                analyzing_cameras += 1
        
        # Son 24 saatteki analiz sayısı
        yesterday = datetime.utcnow() - timedelta(days=1)
        total_analyses = 0
        
        for camera in cameras:
            history = analysis_engine.get_analysis_history(camera.camera_id, 1000)
            recent_analyses = [
                h for h in history 
                if datetime.fromisoformat(h['timestamp'].replace('Z', '+00:00')) > yesterday
            ]
            total_analyses += len(recent_analyses)
        
        stats = {
            'total_cameras': len(cameras),
            'active_cameras': active_cameras,
            'analyzing_cameras': analyzing_cameras,
            'analyses_last_24h': total_analyses,
            'system_uptime': 'running'  # Basit uptime
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# Hata yakalama
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint bulunamadı'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Sunucu hatası'
    }), 500


if __name__ == '__main__':
    # Veritabanı tablolarını oluştur
    db_manager.create_tables()
    
    # Örnek kameralar ekle (test için)
    sample_cameras = [
        {
            'camera_id': 'karasu_1',
            'name': 'Karasu Sahil Kamerası',
            'location': 'Karasu',
            'ip_address': '192.168.1.100',
            'port': 80
        },
        {
            'camera_id': 'sakarya_1',
            'name': 'Sakarya Merkez Kamerası',
            'location': 'Sakarya',
            'ip_address': '192.168.1.101',
            'port': 80
        },
        {
            'camera_id': 'florya_1',
            'name': 'Florya Sahil Kamerası',
            'location': 'Florya',
            'ip_address': '192.168.1.102',
            'port': 80
        }
    ]
    
    # Örnek kameraları ekle (eğer yoksa)
    for camera_data in sample_cameras:
        existing = db_manager.get_camera(camera_data['camera_id'])
        if not existing:
            db_manager.add_camera(camera_data)
            analysis_engine.add_camera(
                camera_data['camera_id'],
                camera_data['ip_address'],
                camera_data['port']
            )
    
    # Flask uygulamasını başlat
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 