"""
ESP32-CAM Entegrasyon Modülü

Bu modül ESP32-CAM'den görüntü almak ve yönetmek için kullanılır.
"""

import cv2
import requests
import numpy as np
from typing import Optional, Dict, Any
import time
import threading
from urllib.parse import urljoin


class ESP32Camera:
    """ESP32-CAM yönetimi sınıfı"""
    
    def __init__(self, ip_address: str, port: int = 80, username: str = None, password: str = None):
        """
        Args:
            ip_address: ESP32-CAM'in IP adresi
            port: Port numarası (varsayılan: 80)
            username: Kullanıcı adı (eğer authentication varsa)
            password: Şifre (eğer authentication varsa)
        """
        self.ip_address = ip_address
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{ip_address}:{port}"
        
        # Stream URL'leri
        self.stream_url = urljoin(self.base_url, "stream")
        self.snapshot_url = urljoin(self.base_url, "capture")
        self.control_url = urljoin(self.base_url, "control")
        
        # Authentication
        self.auth = None
        if username and password:
            self.auth = (username, password)
        
        # Stream durumu
        self.is_streaming = False
        self.stream_thread = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
    def test_connection(self) -> Dict[str, Any]:
        """
        ESP32-CAM bağlantısını test eder
        
        Returns:
            Bağlantı durumu
        """
        try:
            # Basit bir HTTP isteği gönder
            response = requests.get(self.base_url, timeout=5, auth=self.auth)
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'message': 'ESP32-CAM bağlantısı başarılı',
                    'ip': self.ip_address,
                    'port': self.port
                }
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code} hatası',
                    'ip': self.ip_address,
                    'port': self.port
                }
                
        except requests.exceptions.ConnectionError:
            return {
                'status': 'error',
                'message': 'ESP32-CAM bağlantısı kurulamadı',
                'ip': self.ip_address,
                'port': self.port
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Bağlantı hatası: {str(e)}',
                'ip': self.ip_address,
                'port': self.port
            }
    
    def capture_snapshot(self) -> Optional[np.ndarray]:
        """
        Tek bir fotoğraf çeker
        
        Returns:
            Çekilen görüntü (numpy array) veya None
        """
        try:
            response = requests.get(self.snapshot_url, timeout=10, auth=self.auth)
            
            if response.status_code == 200:
                # JPEG verisini numpy array'e çevir
                image_array = np.frombuffer(response.content, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                return image
            else:
                print(f"Fotoğraf çekme hatası: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Fotoğraf çekme hatası: {e}")
            return None
    
    def start_stream(self) -> bool:
        """
        Video stream'ini başlatır
        
        Returns:
            Başarı durumu
        """
        if self.is_streaming:
            return True
            
        try:
            self.is_streaming = True
            self.stream_thread = threading.Thread(target=self._stream_worker)
            self.stream_thread.daemon = True
            self.stream_thread.start()
            return True
        except Exception as e:
            print(f"Stream başlatma hatası: {e}")
            self.is_streaming = False
            return False
    
    def stop_stream(self):
        """Video stream'ini durdurur"""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=2)
    
    def _stream_worker(self):
        """Stream worker thread"""
        try:
            # OpenCV VideoCapture kullanarak stream'i aç
            stream_url = f"http://{self.ip_address}:{self.port}/stream"
            cap = cv2.VideoCapture(stream_url)
            
            if not cap.isOpened():
                print("Stream açılamadı")
                self.is_streaming = False
                return
            
            while self.is_streaming:
                ret, frame = cap.read()
                if ret:
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                else:
                    time.sleep(0.1)
            
            cap.release()
            
        except Exception as e:
            print(f"Stream worker hatası: {e}")
            self.is_streaming = False
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Mevcut frame'i döner
        
        Returns:
            Mevcut frame veya None
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def set_camera_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Kamera ayarlarını değiştirir
        
        Args:
            settings: Ayarlar sözlüğü
            
        Returns:
            Başarı durumu
        """
        try:
            response = requests.post(
                self.control_url,
                json=settings,
                timeout=5,
                auth=self.auth
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Kamera ayarları hatası: {e}")
            return False
    
    def get_camera_info(self) -> Dict[str, Any]:
        """
        Kamera bilgilerini alır
        
        Returns:
            Kamera bilgileri
        """
        try:
            info_url = urljoin(self.base_url, "info")
            response = requests.get(info_url, timeout=5, auth=self.auth)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'status': 'error',
                    'message': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def is_connected(self) -> bool:
        """
        Kamera bağlantı durumunu kontrol eder
        
        Returns:
            Bağlantı durumu
        """
        result = self.test_connection()
        return result['status'] == 'success'


class CameraManager:
    """Çoklu kamera yöneticisi"""
    
    def __init__(self):
        self.cameras = {}
        
    def add_camera(self, camera_id: str, ip_address: str, port: int = 80, 
                   username: str = None, password: str = None) -> bool:
        """
        Yeni kamera ekler
        
        Args:
            camera_id: Kamera benzersiz ID'si
            ip_address: IP adresi
            port: Port numarası
            username: Kullanıcı adı
            password: Şifre
            
        Returns:
            Başarı durumu
        """
        try:
            camera = ESP32Camera(ip_address, port, username, password)
            
            # Bağlantıyı test et
            if camera.test_connection()['status'] == 'success':
                self.cameras[camera_id] = camera
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Kamera ekleme hatası: {e}")
            return False
    
    def remove_camera(self, camera_id: str):
        """Kamerayı kaldırır"""
        if camera_id in self.cameras:
            self.cameras[camera_id].stop_stream()
            del self.cameras[camera_id]
    
    def get_camera(self, camera_id: str) -> Optional[ESP32Camera]:
        """Kamerayı döner"""
        return self.cameras.get(camera_id)
    
    def get_all_cameras(self) -> Dict[str, ESP32Camera]:
        """Tüm kameraları döner"""
        return self.cameras.copy()
    
    def get_camera_status(self, camera_id: str) -> Dict[str, Any]:
        """Kamera durumunu döner"""
        camera = self.get_camera(camera_id)
        if camera:
            return {
                'id': camera_id,
                'ip': camera.ip_address,
                'connected': camera.is_connected(),
                'streaming': camera.is_streaming
            }
        else:
            return {
                'id': camera_id,
                'connected': False,
                'error': 'Kamera bulunamadı'
            } 