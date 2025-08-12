# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, DateField, FloatField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Optional

class RegistrationForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    logo = FileField('Logo (optional)')
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BillUploadForm(FlaskForm):
    bill_file = FileField('Upload Bill', validators=[DataRequired()])
    submit = SubmitField('Process Bill')

class BillEditForm(FlaskForm):
    bill_file_path = HiddenField()
    bill_date = DateField('Bill Date', validators=[Optional()])
    bill_number = StringField('Bill Number', validators=[Optional()])
    electricity_usage_value = FloatField('Electricity Usage', validators=[Optional()])
    electricity_usage_unit = SelectField('Unit', choices=[('kWh', 'kWh')], validators=[Optional()])
    water_usage_value = FloatField('Water Usage', validators=[Optional()])
    water_usage_unit = SelectField('Unit', choices=[('liters', 'liters'), ('m3', 'm³')], validators=[Optional()])
    methane_usage_value = FloatField('Methane Usage', validators=[Optional()])
    methane_usage_unit = SelectField('Unit', choices=[('m3', 'm³'), ('kg', 'kg')], validators=[Optional()])
    oil_usage_value = FloatField('Oil Usage', validators=[Optional()])
    oil_usage_unit = SelectField('Unit', choices=[('liters', 'liters'), ('kg', 'kg')], validators=[Optional()])
    coal_usage_value = FloatField('Coal Usage', validators=[Optional()])
    coal_usage_unit = SelectField('Unit', choices=[('kg', 'kg'), ('tons', 'tons')], validators=[Optional()])
    industrial_waste_value = FloatField('Industrial Waste', validators=[Optional()])
    industrial_waste_unit = SelectField('Unit', choices=[('kg', 'kg'), ('tons', 'tons')], validators=[Optional()])
    trade_co2_value = FloatField('Trade CO2 Value (tons)', validators=[Optional()])
    natural_gas_usage_value = FloatField('Natural Gas Usage', validators=[Optional()])
    natural_gas_usage_unit = SelectField('Unit', choices=[('m3', 'm³'), ('kg', 'kg')], validators=[Optional()])
    petrol_usage_value = FloatField('Petrol Usage', validators=[Optional()])
    petrol_usage_unit = SelectField('Unit', choices=[('liters', 'liters'), ('kg', 'kg')], validators=[Optional()])
    diesel_usage_value = FloatField('Diesel Usage', validators=[Optional()])
    diesel_usage_unit = SelectField('Unit', choices=[('liters', 'liters'), ('kg', 'kg')], validators=[Optional()])
    billing_period_start = DateField('Billing Period Start', validators=[Optional()])
    billing_period_end = DateField('Billing Period End', validators=[Optional()])
    submit = SubmitField('Save')