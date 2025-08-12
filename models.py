# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    logo_path = db.Column(db.String(200), default='defaultlogo.png')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login required properties
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class BillRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bill_date = db.Column(db.Date)
    bill_number = db.Column(db.String(50))
    electricity_usage_value = db.Column(db.Float)
    electricity_usage_unit = db.Column(db.String(20))
    water_usage_value = db.Column(db.Float)
    water_usage_unit = db.Column(db.String(20))
    methane_usage_value = db.Column(db.Float)
    methane_usage_unit = db.Column(db.String(20))
    oil_usage_value = db.Column(db.Float)
    oil_usage_unit = db.Column(db.String(20))
    coal_usage_value = db.Column(db.Float)
    coal_usage_unit = db.Column(db.String(20))
    industrial_waste_value = db.Column(db.Float)
    industrial_waste_unit = db.Column(db.String(20))
    trade_co2_value = db.Column(db.Float)
    natural_gas_usage_value = db.Column(db.Float)
    natural_gas_usage_unit = db.Column(db.String(20))
    petrol_usage_value = db.Column(db.Float)
    petrol_usage_unit = db.Column(db.String(20))
    diesel_usage_value = db.Column(db.Float)
    diesel_usage_unit = db.Column(db.String(20))
    billing_period_start = db.Column(db.Date)
    billing_period_end = db.Column(db.Date)
    total_co2_tonnes = db.Column(db.Float, default=0.0)
    total_emission_kgco2e = db.Column(db.Float, default=0.0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    bill_file_path = db.Column(db.String(200))