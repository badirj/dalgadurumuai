"""
Ana Analiz Motoru

Bu modül dalga analizi ve insan tespiti işlemlerini koordine eder.
"""

import cv2
import numpy as np
import time
import threading
from typing import Dict, Any, Optional, List
import os
from datetime import datetime

from wave_analyzer import WaveIntensityAnalyzer
from people_detector import PeopleDetector
from esp32_camera import ESP32Camera, CameraManager
from database import db_manager, WaveAnalysis


class AnalysisEngine:
    """Ana analiz motoru sınıfı"""
    
    def __init__(self):
        self.wave_analyzer = WaveIntensityAnalyzer()
        self.people_detector = PeopleDetector()
        self.camera_manager = CameraManager()
        
        # Analiz durumu
        self.is_running = False
        self.analysis_threads = {}
        self.analysis_results = {}
        
        # Frame kaydetme ayarları
        self.save_frames = True
        self.frames_dir = "saved_frames"
        os.makedirs(self.frames_dir, exist_ok=True)
        
    def add_camera(self, camera_id: str, ip_address: str, port: int = 80,
                   username: str = None, password: str = None) -> bool:
        """
        Analiz motoruna kamera ekler
        
        Args:
            camera_id: Kamera benzersiz ID'si
            ip_address: IP adresi
            port: Port numarası
            username: Kullanıcı adı
            password: Şifre
            
        Returns:
            Başarı durumu
        """
        success = self.camera_manager.add_camera(camera_id, ip_address, port, username, password)
        if success:
            print(f"Kamera {camera_id} başarıyla eklendi")
        return success
    
    def start_analysis(self, camera_id: str) -> bool:
        """
        Belirtilen kamera için analizi başlatır
        
        Args:
            camera_id: Kamera ID'si
            
        Returns:
            Başarı durumu
        """
        if camera_id in self.analysis_threads and self.analysis_threads[camera_id].is_alive():
            print(f"Kamera {camera_id} için analiz zaten çalışıyor")
            return True
            
        camera = self.camera_manager.get_camera(camera_id)
        if not camera:
            print(f"Kamera {camera_id} bulunamadı")
            return False
            
        # Analiz thread'ini başlat
        analysis_thread = threading.Thread(
            target=self._analysis_worker,
            args=(camera_id,),
            daemon=True
        )
        analysis_thread.start()
        
        self.analysis_threads[camera_id] = analysis_thread
        self.is_running = True
        
        print(f"Kamera {camera_id} için analiz başlatıldı")
        return True
    
    def stop_analysis(self, camera_id: str):
        """Belirtilen kamera için analizi durdurur"""
        if camera_id in self.analysis_threads:
            # Thread'i durdur (daemon thread olduğu için otomatik kapanacak)
            self.analysis_threads.pop(camera_id, None)
            print(f"Kamera {camera_id} için analiz durduruldu")
    
    def stop_all_analysis(self):
        """Tüm analizleri durdurur"""
        self.is_running = False
        self.analysis_threads.clear()
        print("Tüm analizler durduruldu")
    
    def _analysis_worker(self, camera_id: str):
        """Analiz worker thread'i"""
        camera = self.camera_manager.get_camera(camera_id)
        if not camera:
            return
            
        # Stream'i başlat
        if not camera.start_stream():
            print(f"Kamera {camera_id} stream başlatılamadı")
            return
            
        print(f"Kamera {camera_id} analizi başladı")
        
        while self.is_running and camera_id in self.analysis_threads:
            try:
                # Frame al
                frame = camera.get_current_frame()
                if frame is None:
                    time.sleep(1)
                    continue
                
                # Analiz yap
                start_time = time.time()
                analysis_result = self._analyze_frame(frame, camera_id)
                processing_time = time.time() - start_time
                
                # Sonucu kaydet
                analysis_result['processing_time'] = processing_time
                self.analysis_results[camera_id] = analysis_result
                
                # Veritabanına kaydet
                self._save_analysis_to_db(camera_id, analysis_result, frame)
                
                # 5 saniye bekle
                time.sleep(5)
                
            except Exception as e:
                print(f"Kamera {camera_id} analiz hatası: {e}")
                time.sleep(5)
        
        # Stream'i durdur
        camera.stop_stream()
        print(f"Kamera {camera_id} analizi durdu")
    
    def _analyze_frame(self, frame: np.ndarray, camera_id: str) -> Dict[str, Any]:
        """
        Tek bir frame'i analiz eder
        
        Args:
            frame: Analiz edilecek frame
            camera_id: Kamera ID'si
            
        Returns:
            Analiz sonuçları
        """
        # Dalga analizi
        wave_analysis = self.wave_analyzer.analyze_wave_intensity(frame)
        
        # İnsan tespiti
        people_analysis = self.people_detector.detect_people(frame)
        
        # Sonuçları birleştir
        result = {
            'camera_id': camera_id,
            'timestamp': datetime.utcnow(),
            'wave_analysis': wave_analysis,
            'people_analysis': people_analysis,
            'frame_shape': frame.shape
        }
        
        return result
    
    def _save_analysis_to_db(self, camera_id: str, analysis_result: Dict[str, Any], frame: np.ndarray):
        """Analiz sonucunu veritabanına kaydeder"""
        try:
            # Frame'i kaydet
            frame_path = None
            if self.save_frames:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                frame_filename = f"{camera_id}_{timestamp}.jpg"
                frame_path = os.path.join(self.frames_dir, frame_filename)
                cv2.imwrite(frame_path, frame)
            
            # Veritabanı kaydı
            db_data = {
                'camera_id': camera_id,
                'timestamp': analysis_result['timestamp'],
                'current_intensity': analysis_result['wave_analysis']['current_intensity'],
                'average_intensity': analysis_result['wave_analysis']['average_intensity'],
                'motion_score': analysis_result['wave_analysis']['motion_score'],
                'edge_score': analysis_result['wave_analysis']['edge_score'],
                'pattern_score': analysis_result['wave_analysis']['pattern_score'],
                'intensity_level': analysis_result['wave_analysis']['intensity_level'],
                'description': analysis_result['wave_analysis']['description'],
                'people_count': analysis_result['people_analysis']['people_count'],
                'crowd_level': analysis_result['people_analysis']['crowd_level'],
                'crowd_score': analysis_result['people_analysis']['crowd_score'],
                'frame_path': frame_path,
                'processing_time': analysis_result['processing_time']
            }
            
            db_manager.add_wave_analysis(db_data)
            
        except Exception as e:
            print(f"Veritabanı kaydetme hatası: {e}")
    
    def get_latest_result(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """
        Kameranın en son analiz sonucunu getirir
        
        Args:
            camera_id: Kamera ID'si
            
        Returns:
            En son analiz sonucu veya None
        """
        # Önce memory'den kontrol et
        if camera_id in self.analysis_results:
            return self.analysis_results[camera_id]
        
        # Veritabanından getir
        latest_analysis = db_manager.get_latest_analysis(camera_id)
        if latest_analysis:
            return latest_analysis.to_dict()
        
        return None
    
    def get_all_latest_results(self) -> Dict[str, Any]:
        """Tüm kameraların en son sonuçlarını getirir"""
        results = {}
        
        for camera_id in self.camera_manager.get_all_cameras().keys():
            result = self.get_latest_result(camera_id)
            if result:
                results[camera_id] = result
        
        return results
    
    def get_analysis_history(self, camera_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Kameranın analiz geçmişini getirir
        
        Args:
            camera_id: Kamera ID'si
            limit: Maksimum kayıt sayısı
            
        Returns:
            Analiz geçmişi listesi
        """
        analyses = db_manager.get_analysis_history(camera_id, limit)
        return [analysis.to_dict() for analysis in analyses]
    
    def get_camera_status(self, camera_id: str) -> Dict[str, Any]:
        """Kamera durumunu getirir"""
        camera = self.camera_manager.get_camera(camera_id)
        if not camera:
            return {'error': 'Kamera bulunamadı'}
        
        return {
            'camera_id': camera_id,
            'ip_address': camera.ip_address,
            'connected': camera.is_connected(),
            'streaming': camera.is_streaming,
            'analyzing': camera_id in self.analysis_threads and self.analysis_threads[camera_id].is_alive(),
            'last_result': self.get_latest_result(camera_id) is not None
        }
    
    def get_all_camera_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Tüm kameraların durumunu getirir"""
        statuses = {}
        
        for camera_id in self.camera_manager.get_all_cameras().keys():
            statuses[camera_id] = self.get_camera_status(camera_id)
        
        return statuses


# Global analiz motoru örneği
analysis_engine = AnalysisEngine() 