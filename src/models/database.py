from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class DashboardData(db.Model):
    """نموذج لتخزين بيانات لوحة التحكم"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    total_balance = db.Column(db.Float, default=0)
    available_balance = db.Column(db.Float, default=0)
    pnl = db.Column(db.Float, default=0)
    margin_level = db.Column(db.Float, default=0)
    api_status = db.Column(db.Boolean, default=False)
    
    def __init__(self, **kwargs):
        super(DashboardData, self).__init__(**kwargs)

class Position(db.Model):
    """نموذج لتخزين المراكز"""
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20))
    side = db.Column(db.String(10))
    size = db.Column(db.Float)
    entry_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    pnl = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    dashboard_id = db.Column(db.Integer, db.ForeignKey('dashboard_data.id'))

class Event(db.Model):
    """نموذج لتخزين الأحداث"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20))
    last_triggered = db.Column(db.DateTime)
    key = db.Column(db.String(100))

class Action(db.Model):
    """نموذج لتخزين الإجراءات"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20))
    last_run = db.Column(db.DateTime)