#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Big Data Enterprise Security Management System
Böyük Məlumat Əsaslı Müəssisə Təhlükəsizliyi İdarəetmə Sistemi

Əsas tətbiq faylı - Flask web server və API endpoints
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.middleware.proxy_fix import ProxyFix

from app.siem_system import SIEMProcessor
from app.ml_threat_detection import ThreatDetector
from app.risk_assessment import RiskAssessor
from app.data_processor import SecurityDataProcessor
from config.settings import Config

# Flask tətbiqini yaradırıq
app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app)

# CORS və SocketIO konfiqurasiyası
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Əsas komponentləri initialize edirik
siem_processor = SIEMProcessor()
threat_detector = ThreatDetector()
risk_assessor = RiskAssessor()
data_processor = SecurityDataProcessor()

@app.route('/')
def dashboard():
    """Əsas dashboard səhifəsi"""
    return render_template('dashboard.html')

@app.route('/api/security-status')
def get_security_status():
    """Cari təhlükəsizlik statusu"""
    try:
        status = {
            'timestamp': datetime.now().isoformat(),
            'overall_risk_level': risk_assessor.get_current_risk_level(),
            'active_threats': threat_detector.get_active_threats_count(),
            'system_health': siem_processor.get_system_health(),
            'processed_events_24h': siem_processor.get_events_count_24h(),
            'ml_model_accuracy': threat_detector.get_model_accuracy()
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/threat-analysis')
def get_threat_analysis():
    """Təhdid analizi məlumatları"""
    try:
        analysis = threat_detector.analyze_current_threats()
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/risk-assessment')
def get_risk_assessment():
    """Risk qiymətləndirmə nəticələri"""
    try:
        assessment = risk_assessor.generate_risk_report()
        return jsonify(assessment)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['GET'])
def get_security_events():
    """Təhlükəsizlik hadisələrinin siyahısı"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        severity = request.args.get('severity')
        
        events = siem_processor.get_events(
            page=page, 
            per_page=per_page, 
            severity_filter=severity
        )
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def process_security_event():
    """Yeni təhlükəsizlik hadisəsini emal et"""
    try:
        event_data = request.get_json()
        if not event_data:
            return jsonify({'error': 'Event data is required'}), 400
            
        processed_event = siem_processor.process_event(event_data)
        
        # Real-vaxt bildiriş göndər
        socketio.emit('new_security_event', processed_event)
        
        return jsonify({
            'status': 'processed',
            'event_id': processed_event['id'],
            'risk_level': processed_event['risk_level']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml-model/train', methods=['POST'])
def train_ml_model():
    """Maşın öyrənməsi modelini öyrət"""
    try:
        training_params = request.get_json()
        result = threat_detector.train_model(training_params)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ml-model/predict', methods=['POST'])
def predict_threat():
    """Təhdid proqnozlaşdırması"""
    try:
        input_data = request.get_json()
        prediction = threat_detector.predict_threat(input_data)
        return jsonify(prediction)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/dashboard-data')
def get_dashboard_analytics():
    """Dashboard üçün analitik məlumatlar"""
    try:
        analytics = {
            'threat_trends': data_processor.get_threat_trends(),
            'geographic_threats': data_processor.get_geographic_threat_data(),
            'attack_vectors': data_processor.get_attack_vector_stats(),
            'hourly_activity': data_processor.get_hourly_activity_pattern(),
            'top_targets': data_processor.get_top_targeted_assets()
        }
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/generate', methods=['POST'])
def generate_security_report():
    """Təhlükəsizlik hesabatı yaratmaq"""
    try:
        report_params = request.get_json()
        report = data_processor.generate_comprehensive_report(report_params)
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket hadisələri
@socketio.on('connect')
def handle_connect():
    """Kliyent qoşulduqda"""
    emit('status', {'message': 'Connected to Security Management System'})

@socketio.on('disconnect')
def handle_disconnect():
    """Kliyent ayrıldıqda"""
    print('Client disconnected')

@socketio.on('subscribe_alerts')
def handle_subscribe_alerts():
    """Real-vaxt xəbərdarlıqlara abunə ol"""
    emit('subscription_confirmed', {'type': 'security_alerts'})

# Xəta idarəetməsi
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Development server
    print("🚀 Big Data Security Management System başladılır...")
    print("📊 Dashboard: http://localhost:8080")
    print("🔐 API: http://localhost:8080/api/")
    
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=8080, 
        debug=True,
        allow_unsafe_werkzeug=True
    ) 