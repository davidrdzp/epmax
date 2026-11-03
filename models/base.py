"""Instancia compartida de Flask-SQLAlchemy para todos los modelos."""
from flask_sqlalchemy import SQLAlchemy

db: SQLAlchemy = SQLAlchemy()
