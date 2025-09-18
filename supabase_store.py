"""
Supabase/PostgreSQL persistence layer for BIA application.
Uses SQLAlchemy with DATABASE_URL from environment secrets.
"""

import os
import logging
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import create_engine, text, Column, String, Float, Date, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from bia_core.schemas import UserProfile, WasteLog
import bcrypt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    username = Column(String(50), primary_key=True)
    password_hash = Column(String(128), nullable=False)
    entity_name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False)
    waste_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class WasteLogEntry(Base):
    __tablename__ = 'waste_logs'
    
    id = Column(String(50), primary_key=True)  # Will use UUID or composite key
    username = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    waste_tons = Column(Float, nullable=False)
    notes = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

def migrate():
    """Create tables if they don't exist"""
    try:
        logger.info("Running database migrations...")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('users', 'waste_logs')
            """))
            tables = [row[0] for row in result]
            
        if 'users' in tables and 'waste_logs' in tables:
            logger.info("Database migration completed successfully")
            return True
        else:
            logger.error(f"Migration failed. Found tables: {tables}")
            return False
            
    except Exception as e:
        logger.error(f"Migration error: {e}")
        return False

def add_user(username: str, password: str, entity_name: str, city: str, waste_type: str) -> bool:
    """Add a new user to the database"""
    try:
        db = get_db()
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            db.close()
            return False
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create new user
        new_user = User()
        setattr(new_user, 'username', username)
        setattr(new_user, 'password_hash', password_hash)
        setattr(new_user, 'entity_name', entity_name)
        setattr(new_user, 'city', city)
        setattr(new_user, 'waste_type', waste_type)
        
        db.add(new_user)
        db.commit()
        db.close()
        
        logger.info(f"User {username} added successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error adding user {username}: {e}")
        return False

def validate_user(username: str, password: str) -> Optional[UserProfile]:
    """Validate user credentials and return user profile"""
    try:
        db = get_db()
        
        user = db.query(User).filter(User.username == username).first()
        if not user:
            db.close()
            return None
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), getattr(user, 'password_hash').encode('utf-8')):
            profile = UserProfile(
                username=getattr(user, 'username'),
                password_hash='[PROTECTED]',  # Don't expose real hash
                entity_name=getattr(user, 'entity_name'),
                city=getattr(user, 'city'),
                waste_type=getattr(user, 'waste_type').lower()  # Ensure lowercase
            )
            db.close()
            return profile
        
        db.close()
        return None
        
    except Exception as e:
        logger.error(f"Error validating user {username}: {e}")
        return None

def add_waste_log(username: str, log_date: date, waste_tons: float, notes: str = "") -> bool:
    """Add a waste log entry"""
    try:
        db = get_db()
        
        # Create unique ID (username + date)
        log_id = f"{username}_{log_date.isoformat()}"
        
        # Check if log already exists for this date
        existing_log = db.query(WasteLogEntry).filter(
            WasteLogEntry.username == username,
            WasteLogEntry.date == log_date
        ).first()
        
        if existing_log:
            # Update existing log  
            db.query(WasteLogEntry).filter(
                WasteLogEntry.username == username,
                WasteLogEntry.date == log_date
            ).update({
                'waste_tons': waste_tons,
                'notes': notes
            })
            logger.info(f"Updated waste log for {username} on {log_date}")
        else:
            # Create new log
            new_log = WasteLogEntry()
            setattr(new_log, 'id', log_id)
            setattr(new_log, 'username', username)
            setattr(new_log, 'date', log_date)
            setattr(new_log, 'waste_tons', waste_tons)
            setattr(new_log, 'notes', notes)
            db.add(new_log)
            logger.info(f"Added new waste log for {username} on {log_date}")
        
        db.commit()
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"Error adding waste log for {username}: {e}")
        return False

def get_user_logs(username: str) -> List[WasteLog]:
    """Get all waste logs for a user"""
    try:
        db = get_db()
        
        logs = db.query(WasteLogEntry).filter(
            WasteLogEntry.username == username
        ).order_by(WasteLogEntry.date.desc()).all()
        
        result = []
        for log in logs:
            waste_log = WasteLog(
                username=getattr(log, 'username'),
                date=getattr(log, 'date'),
                waste_tons=getattr(log, 'waste_tons'),
                notes=getattr(log, 'notes', '') or ""
            )
            result.append(waste_log)
        
        db.close()
        logger.info(f"Retrieved {len(result)} logs for {username}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting logs for {username}: {e}")
        return []

# SQL for manual table creation (if needed)
CREATE_TABLES_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password_hash VARCHAR(128) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    waste_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Waste logs table
CREATE TABLE IF NOT EXISTS waste_logs (
    id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    waste_tons REAL NOT NULL,
    notes VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE,
    UNIQUE(username, date)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_waste_logs_username ON waste_logs(username);
CREATE INDEX IF NOT EXISTS idx_waste_logs_date ON waste_logs(date);
"""

if __name__ == "__main__":
    # Test migration
    if migrate():
        print("Migration successful!")
    else:
        print("Migration failed!")