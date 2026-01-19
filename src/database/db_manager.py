# src/database/db_manager.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base

class DatabaseManager:
    def __init__(self, db_url='sqlite:///trello_linter.db'):
        self.engine = create_engine(db_url, echo=False)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    def init_db(self):
        """Initialize database tables"""
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get database session"""
        return self.Session()
    
    def close_session(self):
        """Close session"""
        self.Session.remove()
