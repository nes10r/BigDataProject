import os
from datetime import timedelta

class Config:
    """Sistem konfiqurasiya parametrləri"""
    
    # Flask konfiqurasiyası
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database konfiqurasiyası
    MONGODB_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/security_db'
    INFLUXDB_URL = os.environ.get('INFLUXDB_URL') or 'http://localhost:8086'
    INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN') or 'admin-token'
    INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG') or 'security-org'
    INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET') or 'security-events'
    
    # Redis konfiqurasiyası
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Kafka konfiqurasiyası
    KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_SERVERS') or 'localhost:9092'
    KAFKA_TOPIC_EVENTS = 'security-events'
    KAFKA_TOPIC_ALERTS = 'security-alerts'
    
    # ML Model konfiqurasiyası
    ML_MODEL_PATH = 'models/trained_models/'
    ML_RETRAIN_INTERVAL = timedelta(hours=6)
    ML_CONFIDENCE_THRESHOLD = 0.85
    
    # SIEM konfiqurasiyası
    SIEM_LOG_RETENTION_DAYS = 90
    SIEM_BATCH_SIZE = 1000
    SIEM_PROCESSING_INTERVAL = 30  # saniyə
    
    # Risk Assessment konfiqurasiyası
    RISK_ASSESSMENT_INTERVAL = timedelta(minutes=15)
    HIGH_RISK_THRESHOLD = 0.8
    MEDIUM_RISK_THRESHOLD = 0.5
    
    # Təhlükəsizlik konfiqurasiyası
    MAX_LOGIN_ATTEMPTS = 5
    SESSION_TIMEOUT = timedelta(hours=2)
    API_RATE_LIMIT = 1000  # per hour
    
    # Logging konfiqurasiyası
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = 'logs/security_system.log'
    
    # Filesystem paths
    DATA_DIR = 'data/'
    LOG_DATA_DIR = 'data/logs/'
    UPLOAD_DIR = 'data/uploads/'
    EXPORT_DIR = 'data/exports/' 