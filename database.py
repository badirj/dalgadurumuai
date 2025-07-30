"""
Veritabanı Modelleri ve Bağlantısı

Bu modül PostgreSQL veritabanı bağlantısı ve modellerini içerir.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os
from typing import Optional, List, Dict, Any


# Veritabanı bağlantısı
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost/wave_analyzer')

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Camera(Base):
    """Kamera bilgileri tablosu"""
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)  # Karasu, Sakarya, Florya vb.
    ip_address = Column(String, nullable=False)
    port = Column(Integer, default=80)
    username = Column(String, nullable=True)
    password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Kamera bilgilerini sözlük olarak döner"""
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'name': self.name,
            'location': self.location,
            'ip_address': self.ip_address,
            'port': self.port,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WaveAnalysis(Base):
    """Dalga analizi sonuçları tablosu"""
    __tablename__ = "wave_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Dalga analizi sonuçları
    current_intensity = Column(Float, nullable=False)
    average_intensity = Column(Float, nullable=False)
    motion_score = Column(Float, nullable=False)
    edge_score = Column(Float, nullable=False)
    pattern_score = Column(Float, nullable=False)
    intensity_level = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # İnsan tespiti sonuçları
    people_count = Column(Integer, default=0)
    crowd_level = Column(String, nullable=True)
    crowd_score = Column(Float, default=0.0)
    
    # Ek bilgiler
    frame_path = Column(String, nullable=True)  # Analiz edilen frame'in kaydedildiği yol
    processing_time = Column(Float, nullable=True)  # İşlem süresi (saniye)
    
    def to_dict(self) -> Dict[str, Any]:
        """Analiz sonuçlarını sözlük olarak döner"""
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'wave_analysis': {
                'current_intensity': self.current_intensity,
                'average_intensity': self.average_intensity,
                'motion_score': self.motion_score,
                'edge_score': self.edge_score,
                'pattern_score': self.pattern_score,
                'intensity_level': self.intensity_level,
                'description': self.description
            },
            'people_analysis': {
                'people_count': self.people_count,
                'crowd_level': self.crowd_level,
                'crowd_score': self.crowd_score
            },
            'processing_time': self.processing_time,
            'frame_path': self.frame_path
        }


class CameraRequest(Base):
    """Kamera kayıt başvuruları tablosu"""
    __tablename__ = "camera_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    requester_name = Column(String, nullable=False)
    requester_email = Column(String, nullable=False)
    requester_phone = Column(String, nullable=True)
    location_name = Column(String, nullable=False)
    location_address = Column(Text, nullable=False)
    location_description = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(String, default='pending')  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    admin_notes = Column(Text, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Başvuru bilgilerini sözlük olarak döner"""
        return {
            'id': self.id,
            'requester_name': self.requester_name,
            'requester_email': self.requester_email,
            'requester_phone': self.requester_phone,
            'location_name': self.location_name,
            'location_address': self.location_address,
            'location_description': self.location_description,
            'reason': self.reason,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'admin_notes': self.admin_notes
        }


# Veritabanı işlemleri için yardımcı fonksiyonlar
def get_db() -> Session:
    """Veritabanı oturumu döner"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """Veritabanı yöneticisi sınıfı"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def create_tables(self):
        """Tüm tabloları oluşturur"""
        Base.metadata.create_all(bind=self.engine)
    
    def add_camera(self, camera_data: Dict[str, Any]) -> Optional[Camera]:
        """Yeni kamera ekler"""
        db = self.SessionLocal()
        try:
            camera = Camera(**camera_data)
            db.add(camera)
            db.commit()
            db.refresh(camera)
            return camera
        except Exception as e:
            db.rollback()
            print(f"Kamera ekleme hatası: {e}")
            return None
        finally:
            db.close()
    
    def get_camera(self, camera_id: str) -> Optional[Camera]:
        """Kamera bilgilerini getirir"""
        db = self.SessionLocal()
        try:
            return db.query(Camera).filter(Camera.camera_id == camera_id).first()
        finally:
            db.close()
    
    def get_all_cameras(self) -> List[Camera]:
        """Tüm aktif kameraları getirir"""
        db = self.SessionLocal()
        try:
            return db.query(Camera).filter(Camera.is_active == True).all()
        finally:
            db.close()
    
    def add_wave_analysis(self, analysis_data: Dict[str, Any]) -> Optional[WaveAnalysis]:
        """Dalga analizi sonucu ekler"""
        db = self.SessionLocal()
        try:
            analysis = WaveAnalysis(**analysis_data)
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            return analysis
        except Exception as e:
            db.rollback()
            print(f"Analiz ekleme hatası: {e}")
            return None
        finally:
            db.close()
    
    def get_latest_analysis(self, camera_id: str) -> Optional[WaveAnalysis]:
        """Kameranın en son analiz sonucunu getirir"""
        db = self.SessionLocal()
        try:
            return db.query(WaveAnalysis)\
                    .filter(WaveAnalysis.camera_id == camera_id)\
                    .order_by(WaveAnalysis.timestamp.desc())\
                    .first()
        finally:
            db.close()
    
    def get_analysis_history(self, camera_id: str, limit: int = 100) -> List[WaveAnalysis]:
        """Kameranın analiz geçmişini getirir"""
        db = self.SessionLocal()
        try:
            return db.query(WaveAnalysis)\
                    .filter(WaveAnalysis.camera_id == camera_id)\
                    .order_by(WaveAnalysis.timestamp.desc())\
                    .limit(limit)\
                    .all()
        finally:
            db.close()
    
    def add_camera_request(self, request_data: Dict[str, Any]) -> Optional[CameraRequest]:
        """Kamera kayıt başvurusu ekler"""
        db = self.SessionLocal()
        try:
            request = CameraRequest(**request_data)
            db.add(request)
            db.commit()
            db.refresh(request)
            return request
        except Exception as e:
            db.rollback()
            print(f"Başvuru ekleme hatası: {e}")
            return None
        finally:
            db.close()
    
    def get_pending_requests(self) -> List[CameraRequest]:
        """Bekleyen başvuruları getirir"""
        db = self.SessionLocal()
        try:
            return db.query(CameraRequest)\
                    .filter(CameraRequest.status == 'pending')\
                    .order_by(CameraRequest.created_at.desc())\
                    .all()
        finally:
            db.close()
    
    def update_request_status(self, request_id: int, status: str, admin_notes: str = None) -> bool:
        """Başvuru durumunu günceller"""
        db = self.SessionLocal()
        try:
            request = db.query(CameraRequest).filter(CameraRequest.id == request_id).first()
            if request:
                request.status = status
                request.admin_notes = admin_notes
                request.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"Başvuru güncelleme hatası: {e}")
            return False
        finally:
            db.close()


# Veritabanı yöneticisi örneği
db_manager = DatabaseManager() 