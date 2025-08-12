# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///carbonranker.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    OCR_SPACE_API_KEY = os.environ.get('OCR_SPACE_API_KEY')  # Set your OCR Space API key here
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')  # Set