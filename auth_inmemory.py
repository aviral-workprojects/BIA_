"""
In-memory authentication system for BIA application.
Uses bcrypt for password hashing and Streamlit cache for thread-safe storage.
"""

import bcrypt
import streamlit as st
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from bia_core.schemas import UserProfile, WasteLog

@st.cache_resource
def get_auth_store():
    """Get thread-safe authentication store"""
    return {
        'users': {},
        'waste_logs': []
    }

class AuthStore:
    """Thread-safe authentication and data store"""
    
    def __init__(self):
        self.store = get_auth_store()
        self._init_demo_user()
    
    def _init_demo_user(self):
        """Initialize demo user if not exists"""
        if 'demo' not in self.store['users']:
            # Hash the demo password
            password_hash = bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt())
            
            demo_profile = UserProfile(
                username='demo',
                password_hash=password_hash.decode('utf-8'),
                entity_name='Demo Bio-energy Corp',
                city='Mumbai',
                waste_type='organic'
            )
            
            self.store['users']['demo'] = demo_profile
    
    def add_user(self, username: str, password: str, entity_name: str, 
                 city: str, waste_type: str) -> bool:
        """Add new user with hashed password"""
        if username in self.store['users']:
            return False
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        user_profile = UserProfile(
            username=username,
            password_hash=password_hash.decode('utf-8'),
            entity_name=entity_name,
            city=city,
            waste_type=waste_type
        )
        
        self.store['users'][username] = user_profile
        return True
    
    def validate_user(self, username: str, password: str) -> Optional[UserProfile]:
        """Validate user credentials"""
        if username not in self.store['users']:
            return None
        
        user_profile = self.store['users'][username]
        
        # Check password
        if bcrypt.checkpw(password.encode('utf-8'), user_profile.password_hash.encode('utf-8')):
            return user_profile
        
        return None
    
    def add_waste_log(self, waste_log: WasteLog):
        """Add waste log entry"""
        self.store['waste_logs'].append(waste_log)
    
    def get_user_logs(self, username: str) -> List[WasteLog]:
        """Get all waste logs for a user"""
        return [log for log in self.store['waste_logs'] if log.username == username]

# Global auth store instance
auth_store = AuthStore()

def add_user(username: str, password: str, entity_name: str, 
             city: str, waste_type: str) -> bool:
    """Add new user"""
    return auth_store.add_user(username, password, entity_name, city, waste_type)

def validate_user(username: str, password: str) -> Optional[UserProfile]:
    """Validate user credentials"""
    return auth_store.validate_user(username, password)

def add_waste_log(waste_log: WasteLog):
    """Add waste log"""
    auth_store.add_waste_log(waste_log)

def get_user_logs(username: str) -> List[WasteLog]:
    """Get user's waste logs"""
    return auth_store.get_user_logs(username)
