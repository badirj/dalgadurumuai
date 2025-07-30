"""
İnsan Tespiti ve Kalabalık Analizi Modülü

Bu modül görüntüdeki insanları tespit eder ve kalabalık seviyesini analiz eder.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Any
from ultralytics import YOLO
import os


class PeopleDetector:
    """İnsan tespiti ve kalabalık analizi sınıfı"""
    
    def __init__(self, model_path: str = None):
        """
        Args:
            model_path: YOLO model dosyasının yolu (None ise varsayılan kullanılır)
        """
        self.model = None
        self.initialize_model(model_path)
        
    def initialize_model(self, model_path: str = None):
        """YOLO modelini başlatır"""
        try:
            if model_path and os.path.exists(model_path):
                self.model = YOLO(model_path)
            else:
                # Varsayılan YOLO modelini kullan
                self.model = YOLO('yolov8n.pt')
            print("YOLO modeli başarıyla yüklendi")
        except Exception as e:
            print(f"Model yükleme hatası: {e}")
            self.model = None
    
    def detect_people(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Frame'deki insanları tespit eder
        
        Args:
            frame: Analiz edilecek frame
            
        Returns:
            Tespit sonuçları sözlüğü
        """
        if self.model is None:
            return {
                'people_count': 0,
                'crowd_level': 'Bilinmiyor',
                'crowd_score': 0,
                'detections': [],
                'error': 'Model yüklenemedi'
            }
        
        try:
            # YOLO ile tespit yap
            results = self.model(frame, classes=[0])  # Sadece person sınıfı (class 0)
            
            detections = []
            people_count = 0
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Sadece yüksek güvenilirlikli tespitleri al
                        if box.conf[0] > 0.5:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            confidence = box.conf[0].cpu().numpy()
                            
                            detections.append({
                                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                'confidence': float(confidence)
                            })
                            people_count += 1
            
            # Kalabalık seviyesi analizi
            crowd_analysis = self._analyze_crowd_level(people_count, frame.shape)
            
            return {
                'people_count': people_count,
                'crowd_level': crowd_analysis['level'],
                'crowd_score': crowd_analysis['score'],
                'detections': detections,
                'error': None
            }
            
        except Exception as e:
            return {
                'people_count': 0,
                'crowd_level': 'Hata',
                'crowd_score': 0,
                'detections': [],
                'error': str(e)
            }
    
    def _analyze_crowd_level(self, people_count: int, frame_shape: Tuple[int, int, int]) -> Dict[str, Any]:
        """
        Kalabalık seviyesini analiz eder
        
        Args:
            people_count: Tespit edilen insan sayısı
            frame_shape: Frame boyutları
            
        Returns:
            Kalabalık analizi sonuçları
        """
        # Frame alanını hesapla
        frame_area = frame_shape[0] * frame_shape[1]
        
        # İnsan başına düşen alan (piksel)
        area_per_person = frame_area / max(people_count, 1)
        
        # Kalabalık skoru (0-10 arası)
        if people_count == 0:
            crowd_score = 0
        elif people_count <= 5:
            crowd_score = min(people_count * 1.5, 5)
        elif people_count <= 15:
            crowd_score = 5 + (people_count - 5) * 0.5
        else:
            crowd_score = 10
        
        # Kalabalık seviyesi
        if crowd_score < 2:
            level = "Boş"
        elif crowd_score < 4:
            level = "Az Kalabalık"
        elif crowd_score < 6:
            level = "Orta Kalabalık"
        elif crowd_score < 8:
            level = "Kalabalık"
        else:
            level = "Çok Kalabalık"
        
        return {
            'level': level,
            'score': round(crowd_score, 2),
            'area_per_person': int(area_per_person)
        }
    
    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Tespit edilen insanları frame üzerine çizer
        
        Args:
            frame: Orijinal frame
            detections: Tespit sonuçları
            
        Returns:
            Çizimli frame
        """
        result_frame = frame.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            
            # Bounding box çiz
            cv2.rectangle(result_frame, 
                         (bbox[0], bbox[1]), 
                         (bbox[2], bbox[3]), 
                         (0, 255, 0), 2)
            
            # Güvenilirlik skorunu yaz
            cv2.putText(result_frame, 
                       f'{confidence:.2f}', 
                       (bbox[0], bbox[1] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, 
                       (0, 255, 0), 
                       2)
        
        return result_frame
    
    def get_crowd_description(self, crowd_level: str, people_count: int) -> str:
        """
        Kalabalık seviyesi için açıklama döner
        
        Args:
            crowd_level: Kalabalık seviyesi
            people_count: İnsan sayısı
            
        Returns:
            Açıklama metni
        """
        descriptions = {
            "Boş": "Hiç kimse görünmüyor, güvenli",
            "Az Kalabalık": f"{people_count} kişi var, rahat",
            "Orta Kalabalık": f"{people_count} kişi var, normal kalabalık",
            "Kalabalık": f"{people_count} kişi var, dikkatli olun",
            "Çok Kalabalık": f"{people_count} kişi var, çok kalabalık"
        }
        
        return descriptions.get(crowd_level, "Bilinmiyor") 