# app.py
import os
import json
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, BillRecord
from forms import RegistrationForm, LoginForm, BillUploadForm, BillEditForm
import google.generativeai as genai
from collections import defaultdict
import os.path

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add custom Jinja2 filters
@app.template_filter('basename')
def basename_filter(path):
    return os.path.basename(path) if path else ''

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'bills'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'logos'), exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.')
            return redirect(url_for('register'))
        user = User(company_name=form.company_name.data, email=form.email.data)
        user.set_password(form.password.data)
        if form.logo.data:
            filename = secure_filename(form.logo.data.filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'logos', filename)
            form.logo.data.save(logo_path)
            user.logo_path = logo_path
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = BillUploadForm()
    if form.validate_on_submit():
        filename = secure_filename(form.bill_file.data.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'bills', filename)
        form.bill_file.data.save(file_path)
        # Process with OCR and Gemini
        ocr_result = ocr_space_extract(file_path)
        if ocr_result['error']:
            flash(ocr_result['error'])
            return redirect(url_for('upload'))
        raw_text = ocr_result['text']
        gemini_result = gemini_extract_details(raw_text)
        if 'error' in gemini_result:
            flash(gemini_result['error'])
            return redirect(url_for('upload'))
        # Store in session for edit
        session['extracted_data'] = gemini_result
        session['bill_file_path'] = file_path
        return redirect(url_for('edit_bill'))
    return render_template('upload.html', form=form)

@app.route('/edit_bill', methods=['GET', 'POST'])
@login_required
def edit_bill():
    form = BillEditForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            bill = BillRecord(user_id=current_user.id)
            bill.bill_date = form.bill_date.data
            bill.bill_number = form.bill_number.data
            bill.electricity_usage_value = form.electricity_usage_value.data
            bill.electricity_usage_unit = form.electricity_usage_unit.data
            bill.water_usage_value = form.water_usage_value.data
            bill.water_usage_unit = form.water_usage_unit.data
            bill.methane_usage_value = form.methane_usage_value.data
            bill.methane_usage_unit = form.methane_usage_unit.data
            bill.oil_usage_value = form.oil_usage_value.data
            bill.oil_usage_unit = form.oil_usage_unit.data
            bill.coal_usage_value = form.coal_usage_value.data
            bill.coal_usage_unit = form.coal_usage_unit.data
            bill.industrial_waste_value = form.industrial_waste_value.data
            bill.industrial_waste_unit = form.industrial_waste_unit.data
            bill.trade_co2_value = form.trade_co2_value.data
            bill.natural_gas_usage_value = form.natural_gas_usage_value.data
            bill.natural_gas_usage_unit = form.natural_gas_usage_unit.data
            bill.petrol_usage_value = form.petrol_usage_value.data
            bill.petrol_usage_unit = form.petrol_usage_unit.data
            bill.diesel_usage_value = form.diesel_usage_value.data
            bill.diesel_usage_unit = form.diesel_usage_unit.data
            bill.billing_period_start = form.billing_period_start.data
            bill.billing_period_end = form.billing_period_end.data
            bill.bill_file_path = form.bill_file_path.data
            totals = calculate_emissions(form.data)
            bill.total_co2_tonnes = totals['co2_tonnes']
            bill.total_emission_kgco2e = totals['emission_kgco2e']
            db.session.add(bill)
            db.session.commit()
            flash('Bill saved successfully.')
            return redirect(url_for('dashboard'))
    else:
        if 'extracted_data' in session:
            extracted = session.pop('extracted_data')
            file_path = session.pop('bill_file_path')
            form.bill_file_path.data = file_path
            if extracted.get('bill_date'):
                try:
                    form.bill_date.data = datetime.strptime(extracted['bill_date'], '%Y-%m-%d').date()
                except:
                    pass
            form.bill_number.data = extracted.get('bill_number', '')
            if extracted.get('electricity_usage_value') is not None:
                form.electricity_usage_value.data = float(extracted['electricity_usage_value'])
            form.electricity_usage_unit.data = extracted.get('electricity_usage_unit', '')
            if extracted.get('water_usage_value') is not None:
                form.water_usage_value.data = float(extracted['water_usage_value'])
            form.water_usage_unit.data = extracted.get('water_usage_unit', '')
            if extracted.get('methane_usage_value') is not None:
                form.methane_usage_value.data = float(extracted['methane_usage_value'])
            form.methane_usage_unit.data = extracted.get('methane_usage_unit', '')
            if extracted.get('oil_usage_value') is not None:
                form.oil_usage_value.data = float(extracted['oil_usage_value'])
            form.oil_usage_unit.data = extracted.get('oil_usage_unit', '')
            if extracted.get('coal_usage_value') is not None:
                form.coal_usage_value.data = float(extracted['coal_usage_value'])
            form.coal_usage_unit.data = extracted.get('coal_usage_unit', '')
            if extracted.get('industrial_waste_value') is not None:
                form.industrial_waste_value.data = float(extracted['industrial_waste_value'])
            form.industrial_waste_unit.data = extracted.get('industrial_waste_unit', '')
            if extracted.get('trade_co2_value') is not None:
                form.trade_co2_value.data = float(extracted['trade_co2_value'])
            if extracted.get('natural_gas_usage_value') is not None:
                form.natural_gas_usage_value.data = float(extracted['natural_gas_usage_value'])
            form.natural_gas_usage_unit.data = extracted.get('natural_gas_usage_unit', '')
            if extracted.get('petrol_usage_value') is not None:
                form.petrol_usage_value.data = float(extracted['petrol_usage_value'])
            form.petrol_usage_unit.data = extracted.get('petrol_usage_unit', '')
            if extracted.get('diesel_usage_value') is not None:
                form.diesel_usage_value.data = float(extracted['diesel_usage_value'])
            form.diesel_usage_unit.data = extracted.get('diesel_usage_unit', '')
            if extracted.get('billing_period_start'):
                try:
                    form.billing_period_start.data = datetime.strptime(extracted['billing_period_start'], '%Y-%m-%d').date()
                except:
                    pass
            if extracted.get('billing_period_end'):
                try:
                    form.billing_period_end.data = datetime.strptime(extracted['billing_period_end'], '%Y-%m-%d').date()
                except:
                    pass
    return render_template('edit_bill.html', form=form)

def calculate_emissions(data):
    df = pd.read_csv('emission_factors.csv')
    co2_tonnes = 0.0
    emission_kgco2e = 0.0
    sources = {
        'Electricity': ('electricity_usage_value', 'electricity_usage_unit'),
        'Water': ('water_usage_value', 'water_usage_unit'),
        'Methane': ('methane_usage_value', 'methane_usage_unit'),
        'Oil': ('oil_usage_value', 'oil_usage_unit'),
        'Coal': ('coal_usage_value', 'coal_usage_unit'),
        'Industrial Waste': ('industrial_waste_value', 'industrial_waste_unit'),
        'Trade CO₂ Value': ('trade_co2_value', None),
        'Natural Gas': ('natural_gas_usage_value', 'natural_gas_usage_unit'),
        'Petrol': ('petrol_usage_value', 'petrol_usage_unit'),
        'Diesel': ('diesel_usage_value', 'diesel_usage_unit'),
    }
    for source, (value_key, unit_key) in sources.items():
        value = data.get(value_key)
        if value:
            unit = data.get(unit_key) if unit_key else 'tons'
            factor_row = df[(df['Energy Source'] == source) & (df['Unit'] == unit)]
            if not factor_row.empty:
                co2_factor = factor_row['CO2 Emission (tonnes)'].values[0]
                footprint_factor = factor_row['Carbon Footprint Value (kg CO2e)'].values[0]
                co2_tonnes += value * co2_factor
                emission_kgco2e += value * footprint_factor
    return {'co2_tonnes': co2_tonnes, 'emission_kgco2e': emission_kgco2e}

def compute_score(total_emission, bill_count):
    # Score = max(0, 100 - (total_emission / scale)) + bill_count_bonus
    # Scale: 5000.0 kg CO2e as reference
    scale = 5000.0
    emission_score = 100 - (total_emission / scale * 100)
    bill_bonus = min(bill_count * 5, 25)
    score = emission_score + bill_bonus
    return max(0, min(100, round(score, 2)))

@app.route('/dashboard')
@login_required
def dashboard():
    bills = BillRecord.query.filter_by(user_id=current_user.id).order_by(BillRecord.bill_date.desc()).all()
    df = pd.read_csv('emission_factors.csv')
    # Line chart: emissions over time (monthly total)
    monthly_emissions = defaultdict(float)
    for bill in bills:
        if bill.bill_date:
            month_key = bill.bill_date.strftime('%Y-%m')
            monthly_emissions[month_key] += bill.total_emission_kgco2e
    line_labels = sorted(monthly_emissions.keys())
    line_data = [monthly_emissions[m] for m in line_labels]

    # Bar chart: breakdown per month per source
    monthly_sources = defaultdict(lambda: defaultdict(float))
    sources_list = ['Electricity', 'Water', 'Methane', 'Oil', 'Coal', 'Industrial Waste', 'Trade CO₂ Value', 'Natural Gas', 'Petrol', 'Diesel']
    source_fields = {
        'Electricity': ('electricity_usage_value', 'electricity_usage_unit'),
        'Water': ('water_usage_value', 'water_usage_unit'),
        'Methane': ('methane_usage_value', 'methane_usage_unit'),
        'Oil': ('oil_usage_value', 'oil_usage_unit'),
        'Coal': ('coal_usage_value', 'coal_usage_unit'),
        'Industrial Waste': ('industrial_waste_value', 'industrial_waste_unit'),
        'Trade CO₂ Value': ('trade_co2_value', None),
        'Natural Gas': ('natural_gas_usage_value', 'natural_gas_usage_unit'),
        'Petrol': ('petrol_usage_value', 'petrol_usage_unit'),
        'Diesel': ('diesel_usage_value', 'diesel_usage_unit'),
    }
    for bill in bills:
        if bill.bill_date:
            month_key = bill.bill_date.strftime('%Y-%m')
            for source in sources_list:
                value_key, unit_key = source_fields[source]
                value = getattr(bill, value_key)
                if value:
                    unit = getattr(bill, unit_key) if unit_key else 'tons'
                    factor_row = df[(df['Energy Source'] == source) & (df['Unit'] == unit)]
                    if not factor_row.empty:
                        footprint_factor = factor_row['Carbon Footprint Value (kg CO2e)'].values[0]
                        monthly_sources[month_key][source] += value * footprint_factor
    bar_labels = sorted(set(monthly_sources.keys()))
    bar_datasets = []
    for source in sources_list:
        data = [monthly_sources[m].get(source, 0) for m in bar_labels]
        bar_datasets.append({'label': source, 'data': data})

    # Pie chart: total contribution per source
    total_sources = defaultdict(float)
    for bill in bills:
        for source in sources_list:
            value_key, unit_key = source_fields[source]
            value = getattr(bill, value_key)
            if value:
                unit = getattr(bill, unit_key) if unit_key else 'tons'
                factor_row = df[(df['Energy Source'] == source) & (df['Unit'] == unit)]
                if not factor_row.empty:
                    footprint_factor = factor_row['Carbon Footprint Value (kg CO2e)'].values[0]
                    total_sources[source] += value * footprint_factor
    pie_labels = list(total_sources.keys())
    pie_data = list(total_sources.values())

    # Trend % change
    if len(line_labels) >= 2:
        last = monthly_emissions[line_labels[-1]]
        prev = monthly_emissions[line_labels[-2]]
        trend_pct = ((last - prev) / prev * 100) if prev != 0 else 0
    else:
        trend_pct = 0

    # Emission intensity score
    total_emission = sum(bill.total_emission_kgco2e for bill in bills)
    bill_count = len(bills)
    score = compute_score(total_emission, bill_count)

    chart_data = {
        'line': {'labels': line_labels, 'data': line_data},
        'bar': {'labels': bar_labels, 'datasets': bar_datasets},
        'pie': {'labels': pie_labels, 'data': pie_data},
        'trend_pct': round(trend_pct, 2),
        'score': score
    }
    return render_template('dashboard.html', chart_data=chart_data, previous_bills=bills)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.all()
    leaderboard_data = []
    for user in users:
        bills = BillRecord.query.filter_by(user_id=user.id).all()
        total_emission = sum(bill.total_emission_kgco2e for bill in bills)
        bill_count = len(bills)
        score = compute_score(total_emission, bill_count)
        leaderboard_data.append({
            'company_name': user.company_name,
            'score': score,
            'total_emission': total_emission,
            'logo_path': user.logo_path
        })
    # Sort by score (descending), then by total_emission (ascending) for tie-breaking
    leaderboard_data.sort(key=lambda x: (x['score'], -x['total_emission']), reverse=True)
    for idx, entry in enumerate(leaderboard_data, start=1):
        entry['rank'] = idx
    return render_template('leaderboard.html', leaderboard=leaderboard_data)

# ocr_space_extract function is already defined above
@app.route('/previous_bills')
@login_required
def previous_bills():
    bills = BillRecord.query.filter_by(user_id=current_user.id).order_by(BillRecord.uploaded_at.desc()).all()
    return render_template('previous_bills.html', bills=bills)

def ocr_space_extract(image_path, api_key=app.config['OCR_SPACE_API_KEY'], language='eng'):
    try:
        payload = {
            'isOverlayRequired': False,
            'apikey': api_key,
            'language': language,
        }
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'file': f},
                data=payload
            )
        result = json.loads(response.content.decode())
        if result.get('IsErroredOnProcessing', True):
            error_msg = result.get('ErrorMessage', ['Unknown error'])[0]
            return {'text': '', 'error': f"OCR.Space error: {error_msg}"}
        parsed_results = result.get('ParsedResults', [])
        if not parsed_results:
            return {'text': '', 'error': 'No parsed results from OCR.Space'}
        extracted_text = parsed_results[0].get('ParsedText', '')
        return {'text': extracted_text, 'error': ''}
    except Exception as e:
        return {'text': '', 'error': f"Extraction failed: {str(e)}"}

def gemini_extract_details(raw_text, gemini_api_key=app.config['GEMINI_API_KEY']):
    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = (
            "Carefully analyze the bill text to extract the following fields. "
            "Identify energy sources based on keywords like 'electricity', 'water', 'methane', 'oil', 'coal', 'industrial waste', 'trade co2', 'natural gas', 'petrol', 'diesel'. "
            "For each usage, extract the numerical quantity value (float) and the exact unit mentioned (e.g., '100 kWh' -> value=100.0, unit='kWh'). "
            "If unit is not explicitly stated, infer it if possible or leave as empty string. "
            "Search for any dates in the bill (e.g., issue date, due date, billing period) and format them as YYYY-MM-DD. Use the most relevant date as bill_date if multiple are present. "
            "For billing period, extract start and end dates if available. "
            "If a field or source is not mentioned or cannot be extracted, use null for numbers/dates and empty string for strings. "
            "Return strictly as a JSON object with these keys:\n"
            "- bill_date (string YYYY-MM-DD or null)\n"
            "- bill_number (string or \"\")\n"
            "- electricity_usage_value (float or null)\n"
            "- electricity_usage_unit (string or \"\")\n"
            "- water_usage_value (float or null)\n"
            "- water_usage_unit (string or \"\")\n"
            "- methane_usage_value (float or null)\n"
            "- methane_usage_unit (string or \"\")\n"
            "- oil_usage_value (float or null)\n"
            "- oil_usage_unit (string or \"\")\n"
            "- coal_usage_value (float or null)\n"
            "- coal_usage_unit (string or \"\")\n"
            "- industrial_waste_value (float or null)\n"
            "- industrial_waste_unit (string or \"\")\n"
            "- trade_co2_value (float or null)\n"
            "- natural_gas_usage_value (float or null)\n"
            "- natural_gas_usage_unit (string or \"\")\n"
            "- petrol_usage_value (float or null)\n"
            "- petrol_usage_unit (string or \"\")\n"
            "- diesel_usage_value (float or null)\n"
            "- diesel_usage_unit (string or \"\")\n"
            "- billing_period_start (string YYYY-MM-DD or null)\n"
            "- billing_period_end (string YYYY-MM-DD or null)\n"
            f"Text:\n{raw_text}"
        )
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        if '```json' in response_text:
            try:
                json_str = response_text.split('```json')[1].split('```')[0].strip()
                extracted = json.loads(json_str)
            except Exception as e:
                return {'error': f"Failed to parse Gemini JSON: {str(e)}"}
        else:
            try:
                extracted = json.loads(response_text)
            except Exception as e:
                return {'error': f"Failed to parse Gemini response: {str(e)}"}
        return extracted
    except Exception as e:
        return {'error': f"Gemini API failed: {str(e)}"}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)