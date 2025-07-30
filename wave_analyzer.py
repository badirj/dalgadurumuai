"""
Dalga Yoğunluğu Analizi Modülü

Bu modül deniz dalgalarının yoğunluğunu 0-10 arası derecelendirir.
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Any
import math


class WaveIntensityAnalyzer:
    """Dalga yoğunluğu analizi sınıfı"""
    
    def __init__(self):
        self.prev_frame = None
        self.frame_count = 0
        self.intensity_history = []
        
    def analyze_wave_intensity(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Tek bir frame'deki dalga yoğunluğunu analiz eder
        
        Args:
            frame: Analiz edilecek frame
            
        Returns:
            Analiz sonuçları sözlüğü
        """
        # Frame'i gri tonlamaya çevir
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()
            
        # Frame'i yeniden boyutlandır (performans için)
        height, width = gray.shape
        scale_factor = 0.5
        small_gray = cv2.resize(gray, (int(width * scale_factor), int(height * scale_factor)))
        
        # Hareket analizi
        motion_score = self._analyze_motion(small_gray)
        
        # Kenar analizi
        edge_score = self._analyze_edges(small_gray)
        
        # Dalga pattern analizi
        pattern_score = self._analyze_wave_patterns(small_gray)
        
        # Toplam yoğunluk hesaplama (0-10 arası)
        total_intensity = self._calculate_total_intensity(motion_score, edge_score, pattern_score)
        
        # Sonucu geçmişe ekle
        self.intensity_history.append(total_intensity)
        if len(self.intensity_history) > 30:  # Son 30 frame'i tut
            self.intensity_history.pop(0)
            
        # Ortalama yoğunluk
        avg_intensity = np.mean(self.intensity_history) if self.intensity_history else total_intensity
        
        return {
            'current_intensity': round(total_intensity, 2),
            'average_intensity': round(avg_intensity, 2),
            'motion_score': round(motion_score, 2),
            'edge_score': round(edge_score, 2),
            'pattern_score': round(pattern_score, 2),
            'intensity_level': self._get_intensity_level(total_intensity),
            'description': self._get_intensity_description(total_intensity)
        }
    
    def _analyze_motion(self, frame: np.ndarray) -> float:
        """Hareket analizi yapar"""
        if self.prev_frame is None:
            self.prev_frame = frame
            return 0.0
            
        # Frame farkını hesapla
        frame_diff = cv2.absdiff(frame, self.prev_frame)
        
        # Hareket miktarını hesapla
        motion_pixels = np.sum(frame_diff > 30)  # Threshold
        total_pixels = frame_diff.size
        
        motion_ratio = motion_pixels / total_pixels
        motion_score = min(motion_ratio * 100, 10.0)  # 0-10 arası
        
        self.prev_frame = frame
        return motion_score
    
    def _analyze_edges(self, frame: np.ndarray) -> float:
        """Kenar analizi yapar"""
        # Canny edge detection
        edges = cv2.Canny(frame, 50, 150)
        
        # Kenar yoğunluğu
        edge_pixels = np.sum(edges > 0)
        total_pixels = edges.size
        
        edge_ratio = edge_pixels / total_pixels
        edge_score = min(edge_ratio * 50, 10.0)  # 0-10 arası
        
        return edge_score
    
    def _analyze_wave_patterns(self, frame: np.ndarray) -> float:
        """Dalga pattern analizi yapar"""
        # FFT kullanarak frekans analizi
        f_transform = np.fft.fft2(frame)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.log(np.abs(f_shift) + 1)
        
        # Yüksek frekans bileşenlerini analiz et
        height, width = magnitude_spectrum.shape
        center_y, center_x = height // 2, width // 2
        
        # Merkez dışındaki alanları analiz et
        outer_region = magnitude_spectrum[
            max(0, center_y - height//4):min(height, center_y + height//4),
            max(0, center_x - width//4):min(width, center_x + width//4)
        ]
        
        # Pattern skoru
        pattern_variance = np.var(outer_region)
        pattern_score = min(pattern_variance / 1000, 10.0)  # 0-10 arası
        
        return pattern_score
    
    def _calculate_total_intensity(self, motion: float, edge: float, pattern: float) -> float:
        """Toplam yoğunluk hesaplar"""
        # Ağırlıklı ortalama
        weights = [0.4, 0.3, 0.3]  # Hareket, kenar, pattern ağırlıkları
        total = motion * weights[0] + edge * weights[1] + pattern * weights[2]
        
        return min(total, 10.0)
    
    def _get_intensity_level(self, intensity: float) -> str:
        """Yoğunluk seviyesini string olarak döner"""
        if intensity < 2:
            return "Sakin"
        elif intensity < 4:
            return "Hafif Dalgalı"
        elif intensity < 6:
            return "Orta Dalgalı"
        elif intensity < 8:
            return "Dalgalı"
        else:
            return "Çok Dalgalı"
    
    def _get_intensity_description(self, intensity: float) -> str:
        """Yoğunluk açıklamasını döner"""
        if intensity < 2:
            return "Deniz çok sakin, dalga yok"
        elif intensity < 4:
            return "Hafif dalgalar var, güvenli"
        elif intensity < 6:
            return "Orta şiddette dalgalar, dikkatli olun"
        elif intensity < 8:
            return "Güçlü dalgalar, dikkat gerekli"
        else:
            return "Çok güçlü dalgalar, tehlikeli" 