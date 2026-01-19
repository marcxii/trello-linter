# src/database/models.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Board(Base):
    __tablename__ = 'boards'
    
    id = Column(Integer, primary_key=True)
    trello_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    overall_score = Column(Float)
    
    lists = relationship("List", back_populates="board", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="board", cascade="all, delete-orphan")

class List(Base):
    __tablename__ = 'lists'
    
    id = Column(Integer, primary_key=True)
    trello_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    board_id = Column(Integer, ForeignKey('boards.id'))
    
    board = relationship("Board", back_populates="lists")
    cards = relationship("Card", back_populates="list", cascade="all, delete-orphan")

class Card(Base):
    __tablename__ = 'cards'
    
    id = Column(Integer, primary_key=True)
    trello_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    list_id = Column(Integer, ForeignKey('lists.id'))
    members = Column(JSON)
    checklists = Column(JSON)
    labels = Column(JSON)
    
    list = relationship("List", back_populates="cards")
    findings = relationship("Finding", back_populates="card", cascade="all, delete-orphan")

class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True)
    board_id = Column(Integer, ForeignKey('boards.id'))
    generated_at = Column(DateTime, default=datetime.utcnow)
    overall_score = Column(Float)
    category_scores = Column(JSON)
    
    board = relationship("Board", back_populates="reports")
    findings = relationship("Finding", back_populates="report", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = 'findings'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'))
    card_id = Column(Integer, ForeignKey('cards.id'))
    rule_name = Column(String(100), nullable=False)
    severity = Column(String(20))  # critical, major, minor
    category = Column(String(50))
    description = Column(Text)
    suggestion = Column(Text)
    
    report = relationship("Report", back_populates="findings")
    card = relationship("Card", back_populates="findings")