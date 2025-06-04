#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk Assessment Framework
Risk qiymətləndirmə və idarəetmə sistemi
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from pymongo import MongoClient
from config.settings import Config

class RiskAssessor:
    """Risk qiymətləndirmə və analiz sistemi"""
    
    def __init__(self):
        self.config = Config()
        self._setup_database()
        self.risk_matrix = self._initialize_risk_matrix()
        self.threat_weights = self._initialize_threat_weights()
        
    def _setup_database(self):
        """Verilənlər bazasını quraşdır"""
        try:
            self.mongo_client = MongoClient(self.config.MONGODB_URI)
            self.mongo_db = self.mongo_client.security_db
            self.events_collection = self.mongo_db.security_events
            self.alerts_collection = self.mongo_db.security_alerts
            self.risk_assessments = self.mongo_db.risk_assessments
        except Exception as e:
            print(f"Risk Assessment DB bağlantı xətası: {e}")
    
    def _initialize_risk_matrix(self) -> Dict:
        """Risk matrisi hazırla"""
        return {
            'impact_levels': {
                'VERY_LOW': 1,
                'LOW': 2,
                'MEDIUM': 3,
                'HIGH': 4,
                'VERY_HIGH': 5
            },
            'likelihood_levels': {
                'VERY_LOW': 1,
                'LOW': 2,
                'MEDIUM': 3,
                'HIGH': 4,
                'VERY_HIGH': 5
            },
            'risk_categories': {
                (1, 1): 'MINIMAL',      # Very Low Impact, Very Low Likelihood
                (1, 2): 'MINIMAL',      # Very Low Impact, Low Likelihood
                (2, 1): 'MINIMAL',      # Low Impact, Very Low Likelihood
                (2, 2): 'LOW',          # Low Impact, Low Likelihood
                (3, 1): 'LOW',          # Medium Impact, Very Low Likelihood
                (1, 3): 'LOW',          # Very Low Impact, Medium Likelihood
                (3, 2): 'MEDIUM',       # Medium Impact, Low Likelihood
                (2, 3): 'MEDIUM',       # Low Impact, Medium Likelihood
                (4, 1): 'MEDIUM',       # High Impact, Very Low Likelihood
                (1, 4): 'MEDIUM',       # Very Low Impact, High Likelihood
                (3, 3): 'HIGH',         # Medium Impact, Medium Likelihood
                (4, 2): 'HIGH',         # High Impact, Low Likelihood
                (2, 4): 'HIGH',         # Low Impact, High Likelihood
                (5, 1): 'HIGH',         # Very High Impact, Very Low Likelihood
                (1, 5): 'HIGH',         # Very Low Impact, Very High Likelihood
                (4, 3): 'CRITICAL',     # High Impact, Medium Likelihood
                (3, 4): 'CRITICAL',     # Medium Impact, High Likelihood
                (5, 2): 'CRITICAL',     # Very High Impact, Low Likelihood
                (2, 5): 'CRITICAL',     # Low Impact, Very High Likelihood
                (4, 4): 'CRITICAL',     # High Impact, High Likelihood
                (5, 3): 'CRITICAL',     # Very High Impact, Medium Likelihood
                (3, 5): 'CRITICAL',     # Medium Impact, Very High Likelihood
                (5, 4): 'CRITICAL',     # Very High Impact, High Likelihood
                (4, 5): 'CRITICAL',     # High Impact, Very High Likelihood
                (5, 5): 'CRITICAL'      # Very High Impact, Very High Likelihood
            }
        }
    
    def _initialize_threat_weights(self) -> Dict:
        """Təhdid növləri üçün çəki ədədləri"""
        return {
            'malware_detected': 0.9,
            'data_exfiltration': 0.95,
            'unauthorized_access': 0.8,
            'login_failed': 0.6,
            'network_anomaly': 0.7,
            'file_access': 0.5,
            'data_transfer': 0.6,
            'system_error': 0.4,
            'privilege_escalation': 0.85,
            'sql_injection': 0.9,
            'ddos_attack': 0.8,
            'unknown': 0.3
        }
    
    def assess_event_risk(self, event: Dict) -> Dict:
        """Hadisə üçün risk qiymətləndirməsi"""
        try:
            # Impact və likelihood hesabla
            impact = self._calculate_impact(event)
            likelihood = self._calculate_likelihood(event)
            
            # Risk kateqoriyasını təyin et
            risk_category = self.risk_matrix['risk_categories'].get(
                (impact, likelihood), 'MEDIUM'
            )
            
            # Risk skorunu hesabla (0-100 skala)
            risk_score = self._calculate_risk_score(impact, likelihood, event)
            
            # Tövsiyələr yarat
            recommendations = self._generate_recommendations(risk_category, event)
            
            risk_assessment = {
                'event_id': event.get('id'),
                'impact_level': impact,
                'likelihood_level': likelihood,
                'risk_category': risk_category,
                'risk_score': risk_score,
                'assessment_timestamp': datetime.now().isoformat(),
                'recommendations': recommendations,
                'threat_type': event.get('event_type', 'unknown'),
                'source_ip': event.get('source_ip'),
                'asset_criticality': event.get('asset_info', {}).get('criticality', 'MEDIUM')
            }
            
            # Assessment-i verilənlər bazasında saxla
            self._store_risk_assessment(risk_assessment)
            
            return risk_assessment
            
        except Exception as e:
            return {'error': f'Risk qiymətləndirmə xətası: {str(e)}'}
    
    def _calculate_impact(self, event: Dict) -> int:
        """Hadisənin təsir səviyyəsini hesabla"""
        base_impact = 2  # MEDIUM səviyyə
        
        # Asset criticality əsaslı təsir
        asset_criticality = event.get('asset_info', {}).get('criticality', 'MEDIUM')
        criticality_impact = {
            'LOW': 1,
            'MEDIUM': 2,
            'HIGH': 4,
            'CRITICAL': 5
        }
        base_impact = criticality_impact.get(asset_criticality, 2)
        
        # Threat type əsaslı təsir
        threat_type = event.get('event_type', 'unknown')
        threat_impact_modifier = {
            'malware_detected': 2,
            'data_exfiltration': 2,
            'unauthorized_access': 1,
            'privilege_escalation': 2,
            'sql_injection': 1,
            'ddos_attack': 1,
            'login_failed': 0,
            'file_access': 0,
            'network_anomaly': 1,
            'unknown': 0
        }
        
        impact_modifier = threat_impact_modifier.get(threat_type, 0)
        final_impact = min(base_impact + impact_modifier, 5)
        
        # User role təsiri
        user_role = event.get('user_info', {}).get('role', 'user')
        if user_role == 'admin':
            final_impact = min(final_impact + 1, 5)
        
        return max(final_impact, 1)
    
    def _calculate_likelihood(self, event: Dict) -> int:
        """Hadisənin baş vermə ehtimalını hesabla"""
        base_likelihood = 2  # MEDIUM səviyyə
        
        # Threat intelligence əsaslı ehtimal
        threat_intel = event.get('threat_intel', {})
        if threat_intel.get('is_malicious'):
            base_likelihood += 2
        
        # Geolocation risk əsaslı ehtimal
        geo_location = event.get('geo_location', {})
        if geo_location.get('is_high_risk_country'):
            base_likelihood += 1
        if geo_location.get('is_vpn'):
            base_likelihood += 1
        
        # Korrelyasiya əsaslı ehtimal
        correlations = event.get('correlations', [])
        if len(correlations) > 0:
            base_likelihood += len(correlations)
        
        # Severity əsaslı ehtimal
        severity = event.get('severity', 'LOW')
        severity_likelihood = {
            'LOW': 1,
            'MEDIUM': 2,
            'HIGH': 4,
            'CRITICAL': 5
        }
        
        severity_impact = severity_likelihood.get(severity, 1)
        final_likelihood = max(base_likelihood, severity_impact)
        
        return min(final_likelihood, 5)
    
    def _calculate_risk_score(self, impact: int, likelihood: int, event: Dict) -> float:
        """0-100 skala ilə risk skoru hesabla"""
        # Əsas risk skoru
        base_score = (impact * likelihood) / 25.0 * 100
        
        # Threat type weight əlavə et
        threat_type = event.get('event_type', 'unknown')
        threat_weight = self.threat_weights.get(threat_type, 0.5)
        
        # Final score hesabla
        final_score = base_score * threat_weight
        
        # Əlavə faktorlar
        if event.get('threat_intel', {}).get('is_malicious'):
            final_score *= 1.2
        
        if len(event.get('correlations', [])) > 2:
            final_score *= 1.1
        
        return min(final_score, 100.0)
    
    def _generate_recommendations(self, risk_category: str, event: Dict) -> List[str]:
        """Risk kateqoriyasına əsasən tövsiyələr yarat"""
        recommendations = []
        
        threat_type = event.get('event_type', 'unknown')
        
        # Ümumi tövsiyələr
        general_recommendations = {
            'MINIMAL': [
                'Hadisəni monitorinq altında saxlayın',
                'Avtomatik log təhlilini davam etdirin'
            ],
            'LOW': [
                'Hadisəni yaxından izləyin',
                'İlkin təhlükəsizlik yoxlaması aparın',
                'Log məlumatlarını ətraflı təhlil edin'
            ],
            'MEDIUM': [
                'Dərhal təhlükəsizlik komandası ilə əlaqə saxlayın',
                'Əlavə monitorinq tədbirləri tətbiq edin',
                'Hadisənin kök səbəbini araşdırın',
                'Əgər lazımdırsa, müvəqqəti məhdudiyyətlər tətbiq edin'
            ],
            'HIGH': [
                'Təcili təhlükəsizlik tədbirləri görün',
                'Hadisəni dərhal incident response komandasına bildirin',
                'Təsirlənən sistemləri izolə edin',
                'Forensic analiz üçün məlumatları qoruyun',
                'Rəhbərliyi məlumatlandırın'
            ],
            'CRITICAL': [
                'DƏRHAl crisis response protokolunu aktivləşdirin',
                'Bütün təsirlənən sistemləri dərhal izolə edin',
                'CEO və CISO-nu dərhal məlumatlandırın',
                'Xarici ekspertlərdən kömək alın',
                'Hüquq məsləhətçisi ilə məsləhətləşin',
                'Media və PR strategiyasını hazırlayın',
                'Müştəri və tərəfdaş şirkətləri məlumatlandırın'
            ]
        }
        
        recommendations.extend(general_recommendations.get(risk_category, []))
        
        # Threat type spesifik tövsiyələr
        threat_specific = {
            'malware_detected': [
                'Antivirus bazalarını yeniləyin',
                'Yoluxmuş sistemləri şəbəkədən ayırın',
                'Malware imzalarını təhlil edin'
            ],
            'unauthorized_access': [
                'İstifadəçi hesablarını yoxlayın',
                'Giriş icazələrini təftış edin',
                'Şübhəli hesabları müvəqqəti bloklayin'
            ],
            'data_exfiltration': [
                'Data Loss Prevention (DLP) sistemlərini aktivləşdirin',
                'Şəbəkə trafikini ətraflı monitorinq edin',
                'Həssas məlumatların yerləşdiyi sistemləri yoxlayın'
            ],
            'login_failed': [
                'IP ünvanını müvəqqəti bloklayin',
                'Brute force hücum alqoritmlərini yoxlayın',
                'Multi-factor authentication tələb edin'
            ]
        }
        
        if threat_type in threat_specific:
            recommendations.extend(threat_specific[threat_type])
        
        return recommendations
    
    def _store_risk_assessment(self, assessment: Dict):
        """Risk qiymətləndirməsini saxla"""
        try:
            self.risk_assessments.insert_one(assessment)
        except Exception as e:
            print(f"Risk assessment saxlama xətası: {e}")
    
    def generate_risk_report(self) -> Dict:
        """Ümumi risk hesabatı yarat"""
        try:
            current_time = datetime.now()
            last_24h = current_time - timedelta(hours=24)
            last_7d = current_time - timedelta(days=7)
            
            # Son 24 saat və 7 günün risk statistikası
            risk_stats_24h = self._get_risk_statistics(last_24h, current_time)
            risk_stats_7d = self._get_risk_statistics(last_7d, current_time)
            
            # Cari risk səviyyəsi
            current_risk_level = self._calculate_current_risk_level()
            
            # Risk trendlərini təhlil et
            risk_trends = self._analyze_risk_trends()
            
            # Top risk sources
            top_risk_sources = self._get_top_risk_sources()
            
            report = {
                'report_timestamp': current_time.isoformat(),
                'current_risk_level': current_risk_level,
                'risk_statistics': {
                    'last_24_hours': risk_stats_24h,
                    'last_7_days': risk_stats_7d
                },
                'risk_trends': risk_trends,
                'top_risk_sources': top_risk_sources,
                'recommendations': self._generate_executive_recommendations(current_risk_level),
                'metrics': {
                    'total_events_analyzed': self._get_total_events_count(),
                    'high_risk_events_24h': risk_stats_24h.get('high_risk_count', 0),
                    'average_risk_score': risk_stats_24h.get('average_risk_score', 0),
                    'risk_trend_direction': risk_trends.get('direction', 'stable')
                }
            }
            
            return report
            
        except Exception as e:
            return {'error': f'Risk hesabat xətası: {str(e)}'}
    
    def _get_risk_statistics(self, start_time: datetime, end_time: datetime) -> Dict:
        """Verilmiş vaxt aralığı üçün risk statistikası"""
        try:
            # Risk assessments-dən statistika topla
            query = {
                'assessment_timestamp': {
                    '$gte': start_time.isoformat(),
                    '$lte': end_time.isoformat()
                }
            }
            
            assessments = list(self.risk_assessments.find(query))
            
            if not assessments:
                return {
                    'total_assessments': 0,
                    'high_risk_count': 0,
                    'average_risk_score': 0,
                    'risk_distribution': {}
                }
            
            # Risk kateqoriya paylanması
            risk_distribution = {}
            total_score = 0
            high_risk_count = 0
            
            for assessment in assessments:
                category = assessment.get('risk_category', 'MEDIUM')
                risk_distribution[category] = risk_distribution.get(category, 0) + 1
                
                risk_score = assessment.get('risk_score', 0)
                total_score += risk_score
                
                if category in ['HIGH', 'CRITICAL']:
                    high_risk_count += 1
            
            return {
                'total_assessments': len(assessments),
                'high_risk_count': high_risk_count,
                'average_risk_score': total_score / len(assessments) if assessments else 0,
                'risk_distribution': risk_distribution
            }
            
        except Exception as e:
            print(f"Risk statistika xətası: {e}")
            return {}
    
    def _calculate_current_risk_level(self) -> str:
        """Cari ümumi risk səviyyəsini hesabla"""
        try:
            # Son 1 saatın risk səviyyəsini hesabla
            current_time = datetime.now()
            last_hour = current_time - timedelta(hours=1)
            
            recent_stats = self._get_risk_statistics(last_hour, current_time)
            
            high_risk_count = recent_stats.get('high_risk_count', 0)
            total_assessments = recent_stats.get('total_assessments', 0)
            avg_risk_score = recent_stats.get('average_risk_score', 0)
            
            # Risk səviyyəsi hesabla
            if total_assessments == 0:
                return 'LOW'
            
            high_risk_ratio = high_risk_count / total_assessments
            
            if avg_risk_score > 80 or high_risk_ratio > 0.3:
                return 'CRITICAL'
            elif avg_risk_score > 60 or high_risk_ratio > 0.2:
                return 'HIGH'
            elif avg_risk_score > 40 or high_risk_ratio > 0.1:
                return 'MEDIUM'
            else:
                return 'LOW'
                
        except Exception as e:
            return 'MEDIUM'  # Default value
    
    def _analyze_risk_trends(self) -> Dict:
        """Risk trendlərini təhlil et"""
        try:
            current_time = datetime.now()
            
            # Son 24 saat və əvvəlki 24 saatı müqayisə et
            last_24h = current_time - timedelta(hours=24)
            prev_24h = current_time - timedelta(hours=48)
            
            current_stats = self._get_risk_statistics(last_24h, current_time)
            previous_stats = self._get_risk_statistics(prev_24h, last_24h)
            
            current_avg = current_stats.get('average_risk_score', 0)
            previous_avg = previous_stats.get('average_risk_score', 0)
            
            if current_avg > previous_avg * 1.1:
                direction = 'increasing'
            elif current_avg < previous_avg * 0.9:
                direction = 'decreasing'
            else:
                direction = 'stable'
            
            change_percentage = ((current_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
            
            return {
                'direction': direction,
                'change_percentage': change_percentage,
                'current_average': current_avg,
                'previous_average': previous_avg
            }
            
        except Exception as e:
            return {'direction': 'stable', 'change_percentage': 0}
    
    def _get_top_risk_sources(self) -> List[Dict]:
        """Ən yüksək riskli mənbələri tap"""
        try:
            # Son 24 saatın məlumatları
            current_time = datetime.now()
            last_24h = current_time - timedelta(hours=24)
            
            query = {
                'assessment_timestamp': {
                    '$gte': last_24h.isoformat(),
                    '$lte': current_time.isoformat()
                },
                'risk_score': {'$gte': 50}  # Yalnız orta və yüksək risk
            }
            
            assessments = list(self.risk_assessments.find(query))
            
            # IP ünvanlarına görə qruplaşdır
            ip_risks = {}
            for assessment in assessments:
                ip = assessment.get('source_ip')
                if ip and ip != 'unknown':
                    if ip not in ip_risks:
                        ip_risks[ip] = {
                            'ip': ip,
                            'total_risk_score': 0,
                            'event_count': 0,
                            'max_risk_score': 0,
                            'threat_types': set()
                        }
                    
                    risk_score = assessment.get('risk_score', 0)
                    ip_risks[ip]['total_risk_score'] += risk_score
                    ip_risks[ip]['event_count'] += 1
                    ip_risks[ip]['max_risk_score'] = max(ip_risks[ip]['max_risk_score'], risk_score)
                    ip_risks[ip]['threat_types'].add(assessment.get('threat_type', 'unknown'))
            
            # Ortalama risk skoruna görə sırala
            top_sources = []
            for ip_data in ip_risks.values():
                ip_data['average_risk_score'] = ip_data['total_risk_score'] / ip_data['event_count']
                ip_data['threat_types'] = list(ip_data['threat_types'])
                top_sources.append(ip_data)
            
            # Ən yüksək ortalama risk skoruna görə sırala
            top_sources.sort(key=lambda x: x['average_risk_score'], reverse=True)
            
            return top_sources[:10]  # Top 10
            
        except Exception as e:
            return []
    
    def _generate_executive_recommendations(self, risk_level: str) -> List[str]:
        """İcra rəhbərliyi üçün tövsiyələr"""
        executive_recommendations = {
            'LOW': [
                'Cari təhlükəsizlik tədbirlərini davam etdirin',
                'Personalın təhlükəsizlik məlumatlılığını artırın',
                'Təhlükəsizlik siyasətlərini yeniləyin'
            ],
            'MEDIUM': [
                'Təhlükəsizlik monitorinqini gücləndin',
                'Incident response planını yeniləyin',
                'Əlavə təhlükəsizlik investisiyalarını nəzərdən keçirin',
                'Üçüncü tərəf təhlükəsizlik auditini planlaşdırın'
            ],
            'HIGH': [
                'Təhlükəsizlik büdcəsini artırın',
                '24/7 SOC (Security Operations Center) yaradın',
                'Cyber insurance siyasətini yeniləyin',
                'Crisis management planını aktivləşdirin',
                'Board of Directors-u məlumatlandırın'
            ],
            'CRITICAL': [
                'DƏRHALİ crisis management komandası yaradın',
                'Xarici cybersecurity ekspertləri cəlb edin',
                'Hüquqi və PR komandası ilə koordinasiya edin',
                'Regulatory bodies ilə əlaqə saxlayın',
                'Business continuity planını aktivləşdirin',
                'Stakeholder-ləri dərhal məlumatlandırın'
            ]
        }
        
        return executive_recommendations.get(risk_level, [])
    
    def _get_total_events_count(self) -> int:
        """Ümumi hadisələrin sayı"""
        try:
            return self.events_collection.count_documents({})
        except:
            return 0
    
    def get_current_risk_level(self) -> str:
        """Cari risk səviyyəsini qaytarır"""
        return self._calculate_current_risk_level() 