#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SIEM (Security Information and Event Management) System
Real-vaxt təhlükəsizlik hadisələrinin emalı və analizi
"""

import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from pymongo import MongoClient
from influxdb_client import InfluxDBClient, Point
from config.settings import Config

class SIEMProcessor:
    """SIEM hadisələrinin emalı və saxlanması"""
    
    def __init__(self):
        self.config = Config()
        self._setup_databases()
        self.event_rules = self._load_correlation_rules()
        
    def _setup_databases(self):
        """Verilənlər bazalarını quraşdır"""
        try:
            # MongoDB bağlantısı
            self.mongo_client = MongoClient(self.config.MONGODB_URI)
            self.mongo_db = self.mongo_client.security_db
            self.events_collection = self.mongo_db.security_events
            self.alerts_collection = self.mongo_db.security_alerts
            
            # InfluxDB bağlantısı (time-series data)
            self.influx_client = InfluxDBClient(
                url=self.config.INFLUXDB_URL,
                token=self.config.INFLUXDB_TOKEN,
                org=self.config.INFLUXDB_ORG
            )
            self.influx_write_api = self.influx_client.write_api()
            self.influx_query_api = self.influx_client.query_api()
            
        except Exception as e:
            print(f"Database bağlantı xətası: {e}")
            
    def _load_correlation_rules(self) -> List[Dict]:
        """Hadisə korrelyasiya qaydalarını yüklə"""
        return [
            {
                'name': 'Multiple Failed Logins',
                'description': 'Eyni IP-dən çoxlu uğursuz giriş cəhdləri',
                'condition': {
                    'event_type': 'login_failed',
                    'count_threshold': 5,
                    'time_window': 300  # 5 dəqiqə
                },
                'severity': 'HIGH',
                'response': 'block_ip'
            },
            {
                'name': 'Suspicious File Access',
                'description': 'Şübhəli fayl girişi pattern-i',
                'condition': {
                    'event_type': 'file_access',
                    'pattern': 'rapid_multiple_access',
                    'file_sensitivity': 'high'
                },
                'severity': 'MEDIUM',
                'response': 'alert_admin'
            },
            {
                'name': 'Data Exfiltration Pattern',
                'description': 'Böyük həcmdə məlumat köçürülməsi',
                'condition': {
                    'event_type': 'data_transfer',
                    'volume_threshold': '100MB',
                    'time_window': 600
                },
                'severity': 'CRITICAL',
                'response': 'immediate_investigation'
            }
        ]
    
    def process_event(self, raw_event: Dict) -> Dict:
        """Təhlükəsizlik hadisəsini emal et"""
        try:
            # Event normalizasiyası
            normalized_event = self._normalize_event(raw_event)
            
            # Enrichment - əlavə məlumatlarla zənginləşdirmə
            enriched_event = self._enrich_event(normalized_event)
            
            # Risk səviyyəsini hesabla
            enriched_event['risk_score'] = self._calculate_risk_score(enriched_event)
            
            # Korrelyasiya analizi
            correlations = self._check_correlations(enriched_event)
            enriched_event['correlations'] = correlations
            
            # MongoDB-də saxla
            self._store_event_mongodb(enriched_event)
            
            # InfluxDB-də time-series məlumat saxla
            self._store_event_influxdb(enriched_event)
            
            # Yüksək risk səviyyəsi varsa alert yarat
            if enriched_event['risk_score'] > 0.7:
                self._create_alert(enriched_event)
            
            return enriched_event
            
        except Exception as e:
            print(f"Event emal xətası: {e}")
            return {'error': str(e)}
    
    def _normalize_event(self, raw_event: Dict) -> Dict:
        """Hadisəni standart formata gətir"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        normalized = {
            'id': event_id,
            'timestamp': timestamp,
            'source_ip': raw_event.get('source_ip', 'unknown'),
            'destination_ip': raw_event.get('destination_ip', 'unknown'),
            'event_type': raw_event.get('event_type', 'generic'),
            'severity': raw_event.get('severity', 'LOW'),
            'description': raw_event.get('description', ''),
            'user_id': raw_event.get('user_id'),
            'asset_id': raw_event.get('asset_id'),
            'raw_data': raw_event
        }
        
        # Hash hesabla
        event_hash = hashlib.md5(
            f"{normalized['source_ip']}{normalized['event_type']}{normalized['timestamp']}".encode()
        ).hexdigest()
        normalized['event_hash'] = event_hash
        
        return normalized
    
    def _enrich_event(self, event: Dict) -> Dict:
        """Hadisəni əlavə məlumatlarla zənginləşdir"""
        # IP geolocation
        if event['source_ip'] != 'unknown':
            event['geo_location'] = self._get_ip_geolocation(event['source_ip'])
        
        # Asset information
        if event['asset_id']:
            event['asset_info'] = self._get_asset_info(event['asset_id'])
        
        # User information
        if event['user_id']:
            event['user_info'] = self._get_user_info(event['user_id'])
        
        # Threat intelligence
        event['threat_intel'] = self._check_threat_intelligence(event)
        
        return event
    
    def _calculate_risk_score(self, event: Dict) -> float:
        """Hadisə üçün risk səviyyəsini hesabla"""
        base_score = 0.1
        
        # Severity əsaslı scoring
        severity_scores = {
            'LOW': 0.2,
            'MEDIUM': 0.5,
            'HIGH': 0.8,
            'CRITICAL': 1.0
        }
        base_score += severity_scores.get(event['severity'], 0.1)
        
        # Threat intelligence əsaslı scoring
        if event.get('threat_intel', {}).get('is_malicious'):
            base_score += 0.4
        
        # Geolocation əsaslı scoring
        geo = event.get('geo_location', {})
        if geo.get('is_high_risk_country'):
            base_score += 0.2
        
        # Asset criticality əsaslı scoring
        asset_info = event.get('asset_info', {})
        if asset_info.get('criticality') == 'HIGH':
            base_score += 0.3
        
        return min(base_score, 1.0)
    
    def _check_correlations(self, event: Dict) -> List[Dict]:
        """Digər hadisələrlə korrelyasiya yoxla"""
        correlations = []
        
        for rule in self.event_rules:
            if self._matches_correlation_rule(event, rule):
                correlations.append({
                    'rule_name': rule['name'],
                    'description': rule['description'],
                    'severity': rule['severity'],
                    'matched_at': datetime.now()
                })
        
        return correlations
    
    def _matches_correlation_rule(self, event: Dict, rule: Dict) -> bool:
        """Hadisənin korrelyasiya qaydasına uyğunluğunu yoxla"""
        condition = rule['condition']
        
        # Event type yoxlaması
        if condition.get('event_type') and event['event_type'] != condition['event_type']:
            return False
        
        # Time window əsaslı yoxlama
        if condition.get('time_window'):
            # Son X saniyədə eyni tip hadisələrin sayını yoxla
            return self._check_time_window_condition(event, condition)
        
        return False
    
    def _check_time_window_condition(self, event: Dict, condition: Dict) -> bool:
        """Time window şərtini yoxla"""
        time_window = condition['time_window']
        count_threshold = condition.get('count_threshold', 1)
        
        start_time = event['timestamp'] - timedelta(seconds=time_window)
        
        # MongoDB-dən eyni şərtlərə uyğun hadisələri tap
        query = {
            'timestamp': {'$gte': start_time, '$lte': event['timestamp']},
            'event_type': condition['event_type'],
            'source_ip': event['source_ip']
        }
        
        count = self.events_collection.count_documents(query)
        return count >= count_threshold
    
    def _store_event_mongodb(self, event: Dict):
        """Hadisəni MongoDB-də saxla"""
        try:
            # DateTime object-ləri string-ə çevir JSON serialization üçün
            event_copy = event.copy()
            event_copy['timestamp'] = event['timestamp'].isoformat()
            if 'correlations' in event_copy:
                for corr in event_copy['correlations']:
                    if 'matched_at' in corr:
                        corr['matched_at'] = corr['matched_at'].isoformat()
            
            self.events_collection.insert_one(event_copy)
        except Exception as e:
            print(f"MongoDB saxlama xətası: {e}")
    
    def _store_event_influxdb(self, event: Dict):
        """Time-series məlumatını InfluxDB-də saxla"""
        try:
            point = Point("security_events") \
                .tag("event_type", event['event_type']) \
                .tag("severity", event['severity']) \
                .tag("source_ip", event['source_ip']) \
                .field("risk_score", float(event['risk_score'])) \
                .field("event_id", event['id']) \
                .time(event['timestamp'])
            
            self.influx_write_api.write(
                bucket=self.config.INFLUXDB_BUCKET,
                record=point
            )
        except Exception as e:
            print(f"InfluxDB saxlama xətası: {e}")
    
    def _create_alert(self, event: Dict):
        """Yüksək risk hadisəsi üçün alert yarat"""
        alert = {
            'id': str(uuid.uuid4()),
            'event_id': event['id'],
            'alert_type': 'HIGH_RISK_EVENT',
            'severity': event['severity'],
            'risk_score': event['risk_score'],
            'description': f"Yüksək risk hadisəsi aşkarlandı: {event['description']}",
            'created_at': datetime.now(),
            'status': 'OPEN',
            'correlations': event.get('correlations', [])
        }
        
        try:
            self.alerts_collection.insert_one(alert)
        except Exception as e:
            print(f"Alert yaratma xətası: {e}")
    
    def get_events(self, page: int = 1, per_page: int = 50, severity_filter: str = None) -> Dict:
        """Hadisələrin siyahısını gətir"""
        try:
            skip = (page - 1) * per_page
            query = {}
            
            if severity_filter:
                query['severity'] = severity_filter
            
            events = list(self.events_collection.find(query)
                         .sort('timestamp', -1)
                         .skip(skip)
                         .limit(per_page))
            
            total_count = self.events_collection.count_documents(query)
            
            return {
                'events': events,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_system_health(self) -> Dict:
        """Sistem sağlamlığı statistikası"""
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            
            return {
                'events_last_hour': self.events_collection.count_documents({
                    'timestamp': {'$gte': hour_ago.isoformat()}
                }),
                'active_alerts': self.alerts_collection.count_documents({
                    'status': 'OPEN'
                }),
                'system_status': 'HEALTHY',
                'last_updated': now.isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_events_count_24h(self) -> int:
        """Son 24 saatda emal edilən hadisələrin sayı"""
        try:
            yesterday = datetime.now() - timedelta(days=1)
            return self.events_collection.count_documents({
                'timestamp': {'$gte': yesterday.isoformat()}
            })
        except Exception as e:
            return 0
    
    # Helper methods
    def _get_ip_geolocation(self, ip: str) -> Dict:
        """IP geolocation məlumatı (mock implementation)"""
        # Real implementasiyada MaxMind və ya digər geolocation service istifadə edilər
        return {
            'country': 'Unknown',
            'city': 'Unknown',
            'is_high_risk_country': False,
            'is_vpn': False
        }
    
    def _get_asset_info(self, asset_id: str) -> Dict:
        """Asset məlumatı (mock implementation)"""
        return {
            'name': f'Asset-{asset_id}',
            'type': 'server',
            'criticality': 'MEDIUM',
            'owner': 'IT Department'
        }
    
    def _get_user_info(self, user_id: str) -> Dict:
        """İstifadəçi məlumatı (mock implementation)"""
        return {
            'username': f'user-{user_id}',
            'department': 'Unknown',
            'role': 'user',
            'last_login': None
        }
    
    def _check_threat_intelligence(self, event: Dict) -> Dict:
        """Threat intelligence yoxlaması (mock implementation)"""
        return {
            'is_malicious': False,
            'threat_type': None,
            'confidence': 0.0,
            'source': 'internal'
        } 