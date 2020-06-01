import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
        __tablename__ = "users"
        username = db.Column(db.String(15), primary_key=True, unique=True, nullable=False)
        password = db.Column(db.String(80), nullable=False)

class BookList (db.Model):
        __tablename = "books"
        isbn = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
        title = db.Column(db.String, nullable=False)
        author = db.Column(db.String, nullable=False)
        year = db.Column(db.Integer, nullable=False)
