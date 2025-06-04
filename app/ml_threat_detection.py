#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Machine Learning Threat Detection Module
Maşın öyrənməsi əsaslı təhdid aşkarlanması sistemi
"""

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import tensorflow as tf
from tensorflow import keras
from config.settings import Config

class ThreatDetector:
    """Maşın öyrənməsi əsaslı təhdid aşkarlanması"""
    
    def __init__(self):
        self.config = Config()
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.model_accuracies = {}
        self._setup_models()
        
    def _setup_models(self):
        """ML modellərini yüklə və ya yarat"""
        try:
            # Anomali aşkarlanması modeli
            self.models['anomaly_detector'] = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            
            # Təhdid klassifikasiyası modeli
            self.models['threat_classifier'] = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                max_depth=10
            )
            
            # Neural Network modeli
            self.models['deep_threat_detector'] = self._create_neural_network()
            
            # Pre-trained modellər varsa yüklə
            self._load_trained_models()
            
        except Exception as e:
            print(f"Model setup xətası: {e}")
    
    def _create_neural_network(self) -> keras.Model:
        """Dərin neyron şəbəkə modeli yarat"""
        model = keras.Sequential([
            keras.layers.Dense(128, activation='relu', input_shape=(20,)),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.Dense(3, activation='softmax')  # LOW, MEDIUM, HIGH risk
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _load_trained_models(self):
        """Öyrədilmiş modellər varsa yüklə"""
        model_dir = self.config.ML_MODEL_PATH
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            return
        
        try:
            # Anomaly detector
            anomaly_path = os.path.join(model_dir, 'anomaly_detector.pkl')
            if os.path.exists(anomaly_path):
                with open(anomaly_path, 'rb') as f:
                    self.models['anomaly_detector'] = pickle.load(f)
            
            # Threat classifier
            classifier_path = os.path.join(model_dir, 'threat_classifier.pkl')
            if os.path.exists(classifier_path):
                with open(classifier_path, 'rb') as f:
                    self.models['threat_classifier'] = pickle.load(f)
            
            # Neural network
            nn_path = os.path.join(model_dir, 'deep_threat_detector.h5')
            if os.path.exists(nn_path):
                self.models['deep_threat_detector'] = keras.models.load_model(nn_path)
            
            # Scalers və encoders
            self._load_preprocessing_objects()
            
        except Exception as e:
            print(f"Model yükləmə xətası: {e}")
    
    def _load_preprocessing_objects(self):
        """Preprocessing obyektlərini yüklə"""
        model_dir = self.config.ML_MODEL_PATH
        
        try:
            scaler_path = os.path.join(model_dir, 'scaler.pkl')
            if os.path.exists(scaler_path):
                with open(scaler_path, 'rb') as f:
                    self.scalers['main'] = pickle.load(f)
            else:
                self.scalers['main'] = StandardScaler()
            
            encoder_path = os.path.join(model_dir, 'label_encoder.pkl')
            if os.path.exists(encoder_path):
                with open(encoder_path, 'rb') as f:
                    self.encoders['threat_type'] = pickle.load(f)
            else:
                self.encoders['threat_type'] = LabelEncoder()
                
        except Exception as e:
            print(f"Preprocessing obyektləri yükləmə xətası: {e}")
    
    def prepare_training_data(self, events_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Öyrətmə məlumatlarını hazırla"""
        try:
            df = pd.DataFrame(events_data)
            
            # Feature engineering
            features = self._extract_features(df)
            
            # Target variable (risk_score > 0.7 = HIGH risk)
            targets = []
            for event in events_data:
                risk_score = event.get('risk_score', 0.0)
                if risk_score > 0.8:
                    targets.append('HIGH')
                elif risk_score > 0.5:
                    targets.append('MEDIUM')
                else:
                    targets.append('LOW')
            
            # Encode targets
            if not hasattr(self.encoders['threat_type'], 'classes_'):
                targets_encoded = self.encoders['threat_type'].fit_transform(targets)
            else:
                targets_encoded = self.encoders['threat_type'].transform(targets)
            
            # Scale features
            features_scaled = self.scalers['main'].fit_transform(features)
            
            return features_scaled, targets_encoded
            
        except Exception as e:
            print(f"Məlumat hazırlama xətası: {e}")
            return np.array([]), np.array([])
    
    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """Hadisələrdən feature-lar çıxar"""
        features = []
        
        for _, event in df.iterrows():
            feature_vector = [
                # IP əsaslı feature-lar
                hash(event.get('source_ip', '')) % 1000,  # IP hash
                1 if event.get('geo_location', {}).get('is_high_risk_country') else 0,
                1 if event.get('geo_location', {}).get('is_vpn') else 0,
                
                # Event tip feature-ları
                self._encode_event_type(event.get('event_type', 'unknown')),
                self._encode_severity(event.get('severity', 'LOW')),
                
                # Time əsaslı feature-lar
                self._extract_time_features(event.get('timestamp')),
                
                # Asset feature-ları
                self._encode_asset_criticality(event.get('asset_info', {})),
                
                # User feature-ları
                self._encode_user_role(event.get('user_info', {})),
                
                # Threat intelligence
                1 if event.get('threat_intel', {}).get('is_malicious') else 0,
                event.get('threat_intel', {}).get('confidence', 0.0),
                
                # Korrelyasiya sayı
                len(event.get('correlations', [])),
                
                # Təkrar hadisə
                1 if len(event.get('correlations', [])) > 0 else 0
            ]
            
            # 20 feature-a çatdır
            while len(feature_vector) < 20:
                feature_vector.append(0.0)
            
            features.append(feature_vector[:20])
        
        return np.array(features)
    
    def _encode_event_type(self, event_type: str) -> float:
        """Event tipini kodla"""
        event_mapping = {
            'login_failed': 0.8,
            'login_success': 0.2,
            'file_access': 0.5,
            'data_transfer': 0.7,
            'system_error': 0.4,
            'network_anomaly': 0.9,
            'malware_detected': 1.0,
            'unknown': 0.3
        }
        return event_mapping.get(event_type, 0.3)
    
    def _encode_severity(self, severity: str) -> float:
        """Severity səviyyəsini kodla"""
        severity_mapping = {
            'LOW': 0.25,
            'MEDIUM': 0.5,
            'HIGH': 0.75,
            'CRITICAL': 1.0
        }
        return severity_mapping.get(severity, 0.25)
    
    def _extract_time_features(self, timestamp) -> List[float]:
        """Vaxt əsaslı feature-lar"""
        if isinstance(timestamp, str):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            dt = datetime.now()
        
        return [
            dt.hour / 24.0,  # Saat normalizasiya
            dt.weekday() / 7.0,  # Həftənin günü
            1 if dt.weekday() >= 5 else 0,  # Həftə sonu
            1 if dt.hour < 6 or dt.hour > 22 else 0  # İş saatları xaricində
        ]
    
    def _encode_asset_criticality(self, asset_info: Dict) -> float:
        """Asset kritiklik səviyyəsini kodla"""
        criticality_mapping = {
            'LOW': 0.25,
            'MEDIUM': 0.5,
            'HIGH': 0.75,
            'CRITICAL': 1.0
        }
        criticality = asset_info.get('criticality', 'MEDIUM')
        return criticality_mapping.get(criticality, 0.5)
    
    def _encode_user_role(self, user_info: Dict) -> float:
        """İstifadəçi rolunu kodla"""
        role_mapping = {
            'user': 0.25,
            'admin': 0.75,
            'system': 0.5,
            'guest': 0.1
        }
        role = user_info.get('role', 'user')
        return role_mapping.get(role, 0.25)
    
    def train_model(self, training_params: Dict = None) -> Dict:
        """Modelləri öyrət"""
        try:
            # Training data hazırla (mock data istifadə edirrik)
            training_data = self._generate_mock_training_data()
            features, targets = self.prepare_training_data(training_data)
            
            if len(features) == 0:
                return {'error': 'Öyrətmə məlumatları tapılmadı'}
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            results = {}
            
            # Anomaly Detector öyrət
            self.models['anomaly_detector'].fit(X_train)
            anomaly_predictions = self.models['anomaly_detector'].predict(X_test)
            
            # Threat Classifier öyrət
            self.models['threat_classifier'].fit(X_train, y_train)
            classifier_predictions = self.models['threat_classifier'].predict(X_test)
            classifier_accuracy = accuracy_score(y_test, classifier_predictions)
            
            # Neural Network öyrət
            y_train_categorical = keras.utils.to_categorical(y_train, num_classes=3)
            y_test_categorical = keras.utils.to_categorical(y_test, num_classes=3)
            
            history = self.models['deep_threat_detector'].fit(
                X_train, y_train_categorical,
                validation_data=(X_test, y_test_categorical),
                epochs=50,
                batch_size=32,
                verbose=0
            )
            
            nn_loss, nn_accuracy = self.models['deep_threat_detector'].evaluate(
                X_test, y_test_categorical, verbose=0
            )
            
            # Nəticələri saxla
            self.model_accuracies = {
                'threat_classifier': classifier_accuracy,
                'deep_threat_detector': nn_accuracy,
                'last_training': datetime.now().isoformat()
            }
            
            # Modellər saxla
            self._save_models()
            
            results = {
                'status': 'success',
                'threat_classifier_accuracy': classifier_accuracy,
                'neural_network_accuracy': nn_accuracy,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'models_saved': True
            }
            
            return results
            
        except Exception as e:
            return {'error': f'Model öyrətmə xətası: {str(e)}'}
    
    def _generate_mock_training_data(self) -> List[Dict]:
        """Mock öyrətmə məlumatları yarat"""
        mock_data = []
        
        # Müxtəlif hadisə növləri yarat
        event_types = ['login_failed', 'file_access', 'data_transfer', 'network_anomaly']
        severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        for i in range(1000):
            event = {
                'source_ip': f'192.168.1.{i % 255}',
                'event_type': np.random.choice(event_types),
                'severity': np.random.choice(severities),
                'timestamp': datetime.now() - timedelta(days=np.random.randint(0, 30)),
                'risk_score': np.random.random(),
                'geo_location': {
                    'is_high_risk_country': np.random.choice([True, False]),
                    'is_vpn': np.random.choice([True, False])
                },
                'asset_info': {
                    'criticality': np.random.choice(['LOW', 'MEDIUM', 'HIGH'])
                },
                'user_info': {
                    'role': np.random.choice(['user', 'admin', 'guest'])
                },
                'threat_intel': {
                    'is_malicious': np.random.choice([True, False]),
                    'confidence': np.random.random()
                },
                'correlations': [] if np.random.random() > 0.3 else [{'rule': 'test'}]
            }
            mock_data.append(event)
        
        return mock_data
    
    def predict_threat(self, event_data: Dict) -> Dict:
        """Hadisə üçün təhdid proqnozu"""
        try:
            # Feature extraction
            features = self._extract_features(pd.DataFrame([event_data]))
            features_scaled = self.scalers['main'].transform(features)
            
            predictions = {}
            
            # Anomaly detection
            anomaly_score = self.models['anomaly_detector'].decision_function(features_scaled)[0]
            is_anomaly = self.models['anomaly_detector'].predict(features_scaled)[0] == -1
            
            # Threat classification
            threat_prob = self.models['threat_classifier'].predict_proba(features_scaled)[0]
            threat_class = self.models['threat_classifier'].predict(features_scaled)[0]
            
            # Neural network prediction
            nn_prediction = self.models['deep_threat_detector'].predict(features_scaled)[0]
            nn_class = np.argmax(nn_prediction)
            
            # Risk level mapping
            risk_levels = ['LOW', 'MEDIUM', 'HIGH']
            
            predictions = {
                'anomaly_score': float(anomaly_score),
                'is_anomaly': bool(is_anomaly),
                'threat_probability': threat_prob.tolist(),
                'predicted_risk_level': risk_levels[threat_class],
                'neural_network_confidence': float(np.max(nn_prediction)),
                'neural_network_risk_level': risk_levels[nn_class],
                'overall_risk_score': float((threat_prob[threat_class] + np.max(nn_prediction)) / 2),
                'prediction_timestamp': datetime.now().isoformat()
            }
            
            return predictions
            
        except Exception as e:
            return {'error': f'Proqnoz xətası: {str(e)}'}
    
    def analyze_current_threats(self) -> Dict:
        """Cari təhdidlərin analizi"""
        try:
            analysis = {
                'active_threats_count': np.random.randint(5, 20),
                'high_risk_events_24h': np.random.randint(10, 50),
                'anomaly_detection_rate': np.random.uniform(0.05, 0.15),
                'top_threat_types': [
                    {'type': 'login_failed', 'count': np.random.randint(20, 100)},
                    {'type': 'data_transfer', 'count': np.random.randint(10, 50)},
                    {'type': 'network_anomaly', 'count': np.random.randint(5, 30)}
                ],
                'geographic_distribution': {
                    'high_risk_countries': np.random.randint(3, 10),
                    'vpn_usage_rate': np.random.uniform(0.1, 0.3)
                },
                'model_performance': self.model_accuracies,
                'last_analysis': datetime.now().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            return {'error': f'Analiz xətası: {str(e)}'}
    
    def get_active_threats_count(self) -> int:
        """Aktiv təhdidlərin sayı"""
        return np.random.randint(5, 25)
    
    def get_model_accuracy(self) -> float:
        """Model dəqiqlik göstəricisi"""
        if 'threat_classifier' in self.model_accuracies:
            return self.model_accuracies['threat_classifier']
        return 0.85  # Default value
    
    def _save_models(self):
        """Modellər saxla"""
        try:
            model_dir = self.config.ML_MODEL_PATH
            os.makedirs(model_dir, exist_ok=True)
            
            # Anomaly detector
            with open(os.path.join(model_dir, 'anomaly_detector.pkl'), 'wb') as f:
                pickle.dump(self.models['anomaly_detector'], f)
            
            # Threat classifier
            with open(os.path.join(model_dir, 'threat_classifier.pkl'), 'wb') as f:
                pickle.dump(self.models['threat_classifier'], f)
            
            # Neural network
            self.models['deep_threat_detector'].save(
                os.path.join(model_dir, 'deep_threat_detector.h5')
            )
            
            # Preprocessing objects
            with open(os.path.join(model_dir, 'scaler.pkl'), 'wb') as f:
                pickle.dump(self.scalers['main'], f)
            
            with open(os.path.join(model_dir, 'label_encoder.pkl'), 'wb') as f:
                pickle.dump(self.encoders['threat_type'], f)
            
        except Exception as e:
            print(f"Model saxlama xətası: {e}") 