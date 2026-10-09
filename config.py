"""Environment based configuration reference for HomeEase."""
import os

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this-key')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'homeease')
