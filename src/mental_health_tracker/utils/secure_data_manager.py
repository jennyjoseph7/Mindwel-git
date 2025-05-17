"""
Secure Data Manager: Handles privacy, encryption, and data compliance

Features:
- End-to-end encryption for sensitive user data
- Data retention and deletion policies
- Anonymization of conversation data
- GDPR/HIPAA-style compliance features
- Audit logging for data access
"""
import os
import json
import logging
import hashlib
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import sqlite3
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

class EncryptionManager:
    """Manages encryption and decryption of sensitive data"""
    
    def __init__(self, secret_key=None, salt=None):
        """
        Initialize the encryption manager
        
        Args:
            secret_key: Secret key for encryption (if None, a new one is generated)
            salt: Salt for key derivation (if None, a new one is generated)
        """
        # Generate or use provided key and salt
        self.secret_key = secret_key or os.urandom(32)
        self.salt = salt or os.urandom(16)
        
        # Generate encryption key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt data
        
        Args:
            data: Data to encrypt (string or JSON-serializable object)
            
        Returns:
            Encrypted data as base64 string
        """
        # Convert data to string if it's not already
        if not isinstance(data, str):
            data = json.dumps(data)
            
        # Encrypt
        encrypted_data = self.cipher.encrypt(data.encode())
        
        # Return as base64 string
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted data as string
        """
        # Decode base64
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data)
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(decoded)
            
            # Return as string
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
    
    def export_keys(self) -> Dict:
        """
        Export encryption keys for backup or transfer
        
        Returns:
            Dict with base64-encoded keys
        """
        return {
            "secret_key": base64.urlsafe_b64encode(self.secret_key).decode(),
            "salt": base64.urlsafe_b64encode(self.salt).decode()
        }
    
    @classmethod
    def from_keys(cls, key_dict: Dict) -> 'EncryptionManager':
        """
        Create encryption manager from exported keys
        
        Args:
            key_dict: Dict with base64-encoded keys
            
        Returns:
            New EncryptionManager instance
        """
        if not key_dict.get("secret_key") or not key_dict.get("salt"):
            raise ValueError("Invalid key dictionary")
            
        secret_key = base64.urlsafe_b64decode(key_dict["secret_key"])
        salt = base64.urlsafe_b64decode(key_dict["salt"])
        
        return cls(secret_key=secret_key, salt=salt)


class DataRetentionPolicy:
    """Defines and enforces data retention policies"""
    
    def __init__(self, policy_config=None):
        """
        Initialize data retention policy
        
        Args:
            policy_config: Configuration for retention periods
        """
        # Default policy configuration
        self.policy_config = policy_config or {
            "chat_history": {
                "retention_period_days": 90,
                "anonymize_after_days": 30,
                "sensitive_fields": ["user_id", "ip_address", "email"]
            },
            "user_profiles": {
                "retention_period_days": 365,
                "anonymize_after_days": 180,
                "sensitive_fields": ["name", "email", "phone", "location"]
            },
            "session_data": {
                "retention_period_days": 30,
                "anonymize_after_days": 7,
                "sensitive_fields": ["ip_address", "user_agent", "location"]
            }
        }
    
    def should_delete(self, data_type: str, timestamp: Union[str, datetime]) -> bool:
        """
        Check if data should be deleted based on retention policy
        
        Args:
            data_type: Type of data (e.g., "chat_history")
            timestamp: Creation timestamp
            
        Returns:
            True if data should be deleted, False otherwise
        """
        if data_type not in self.policy_config:
            # If no specific policy, use default retention of 90 days
            retention_days = 90
        else:
            retention_days = self.policy_config[data_type].get("retention_period_days", 90)
        
        # Parse timestamp if it's a string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                # If timestamp can't be parsed, assume it should be deleted
                return True
        
        # Check if data is older than retention period
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        return timestamp < cutoff_date
    
    def should_anonymize(self, data_type: str, timestamp: Union[str, datetime]) -> bool:
        """
        Check if data should be anonymized based on retention policy
        
        Args:
            data_type: Type of data (e.g., "chat_history")
            timestamp: Creation timestamp
            
        Returns:
            True if data should be anonymized, False otherwise
        """
        if data_type not in self.policy_config:
            # If no specific policy, use default anonymization after 30 days
            anonymize_days = 30
        else:
            anonymize_days = self.policy_config[data_type].get("anonymize_after_days", 30)
        
        # Parse timestamp if it's a string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                # If timestamp can't be parsed, assume it should be anonymized
                return True
        
        # Check if data is older than anonymization period
        cutoff_date = datetime.now() - timedelta(days=anonymize_days)
        return timestamp < cutoff_date
    
    def get_sensitive_fields(self, data_type: str) -> List[str]:
        """
        Get list of sensitive fields for a data type
        
        Args:
            data_type: Type of data (e.g., "chat_history")
            
        Returns:
            List of sensitive field names
        """
        if data_type not in self.policy_config:
            # Default sensitive fields
            return ["user_id", "email", "name", "ip_address"]
        
        return self.policy_config[data_type].get("sensitive_fields", [])
    
    def anonymize_data(self, data: Dict, data_type: str) -> Dict:
        """
        Anonymize sensitive fields in data
        
        Args:
            data: Data to anonymize
            data_type: Type of data (e.g., "chat_history")
            
        Returns:
            Anonymized data
        """
        sensitive_fields = self.get_sensitive_fields(data_type)
        anonymized = data.copy()
        
        for field in sensitive_fields:
            if field in anonymized:
                # Generate consistent anonymous ID using hashing
                if field == "user_id" and anonymized.get(field):
                    # Create consistent anonymized ID
                    hash_input = str(anonymized[field]) + "salt"
                    anonymized[field] = "anon_" + hashlib.sha256(hash_input.encode()).hexdigest()[:8]
                else:
                    # Remove other sensitive fields
                    anonymized[field] = "[REDACTED]"
        
        # Add anonymization metadata
        if "_meta" not in anonymized:
            anonymized["_meta"] = {}
        
        anonymized["_meta"]["anonymized"] = True
        anonymized["_meta"]["anonymized_at"] = datetime.now().isoformat()
        
        return anonymized


class AuditLogger:
    """Logs data access and modifications for compliance and auditing"""
    
    def __init__(self, log_file=None, log_to_db=False, db_path=None):
        """
        Initialize audit logger
        
        Args:
            log_file: Path to log file
            log_to_db: Whether to log to database
            db_path: Path to database file
        """
        self.log_file = log_file
        self.log_to_db = log_to_db
        self.db_path = db_path
        
        # Set up database if needed
        if self.log_to_db and db_path:
            self._setup_db()
    
    def _setup_db(self):
        """Set up audit log database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create audit log table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                action TEXT,
                user_id TEXT,
                data_type TEXT,
                resource_id TEXT,
                details TEXT,
                client_info TEXT
            )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to set up audit database: {str(e)}")
    
    def log_access(self, user_id: str, data_type: str, resource_id: str, 
                 action: str, details: str = None, client_info: Dict = None):
        """
        Log data access event
        
        Args:
            user_id: ID of user accessing data
            data_type: Type of data being accessed
            resource_id: ID of specific resource
            action: Action being performed (read, write, delete)
            details: Additional details
            client_info: Client information (IP, user agent, etc.)
        """
        timestamp = datetime.now().isoformat()
        log_id = str(uuid.uuid4())
        
        log_entry = {
            "id": log_id,
            "timestamp": timestamp,
            "action": action,
            "user_id": user_id,
            "data_type": data_type,
            "resource_id": resource_id,
            "details": details or "",
            "client_info": client_info or {}
        }
        
        # Write to file
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to write to audit log file: {str(e)}")
        
        # Write to database
        if self.log_to_db and self.db_path:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        log_id,
                        timestamp,
                        action,
                        user_id,
                        data_type,
                        resource_id,
                        details or "",
                        json.dumps(client_info) if client_info else "{}"
                    )
                )
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to write to audit database: {str(e)}")
        
        # Also log to application logger
        logger.info(f"AUDIT: {action} {data_type} {resource_id} by {user_id}")
    
    def get_user_access_logs(self, user_id: str, start_date: datetime = None, 
                           end_date: datetime = None) -> List[Dict]:
        """
        Get access logs for a specific user
        
        Args:
            user_id: User ID
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            List of access log entries
        """
        if not self.log_to_db or not self.db_path:
            logger.warning("Database logging not enabled")
            return []
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM audit_logs WHERE user_id = ?"
            params = [user_id]
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
                
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
                
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            # Convert to list of dicts
            columns = ["id", "timestamp", "action", "user_id", "data_type", 
                     "resource_id", "details", "client_info"]
            result = []
            
            for row in rows:
                entry = {}
                for i, col in enumerate(columns):
                    entry[col] = row[i]
                    
                # Parse JSON fields
                try:
                    entry["client_info"] = json.loads(entry["client_info"])
                except:
                    entry["client_info"] = {}
                    
                result.append(entry)
                
            return result
        except Exception as e:
            logger.error(f"Failed to query audit logs: {str(e)}")
            return []


class SecureDataManager:
    """
    Manages secure storage, retrieval, and deletion of sensitive user data
    with privacy compliance features
    """
    
    def __init__(self, db_path=None, encryption_key=None, audit_log_path=None):
        """
        Initialize secure data manager
        
        Args:
            db_path: Path to database file
            encryption_key: Encryption key or dict with keys
            audit_log_path: Path to audit log file
        """
        # Initialize components
        self.db_path = db_path or "secure_data.db"
        
        # Set up encryption manager
        if encryption_key and isinstance(encryption_key, dict):
            self.encryption = EncryptionManager.from_keys(encryption_key)
        else:
            self.encryption = EncryptionManager(secret_key=encryption_key)
            
        # Set up retention policy
        self.retention = DataRetentionPolicy()
        
        # Set up audit logger
        self.audit = AuditLogger(
            log_file=audit_log_path,
            log_to_db=True,
            db_path=self.db_path.replace(".db", "_audit.db")
        )
        
        # Initialize database
        self._setup_database()
        
        # Maintenance tasks
        self._last_maintenance = time.time()
        self._maintenance_interval = 3600  # 1 hour
    
    def _setup_database(self):
        """Set up secure database"""
        try:
            Path(os.path.dirname(self.db_path)).mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                user_id TEXT,
                data_type TEXT,
                data_id TEXT,
                encrypted_data TEXT,
                created_at TEXT,
                updated_at TEXT,
                metadata TEXT,
                PRIMARY KEY (user_id, data_type, data_id)
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS deletion_requests (
                request_id TEXT PRIMARY KEY,
                user_id TEXT,
                request_type TEXT,
                status TEXT,
                created_at TEXT,
                completed_at TEXT
            )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to set up secure database: {str(e)}")
            raise
    
    def store_data(self, user_id: str, data_type: str, data: Dict, 
                 data_id: str = None, client_info: Dict = None) -> str:
        """
        Securely store user data
        
        Args:
            user_id: User ID
            data_type: Type of data (e.g., "chat_history", "user_profile")
            data: Data to store
            data_id: Optional data ID (generated if not provided)
            client_info: Client information for audit log
            
        Returns:
            Data ID
        """
        # Run periodic maintenance if needed
        self._check_maintenance()
        
        # Generate data ID if not provided
        if not data_id:
            data_id = str(uuid.uuid4())
            
        # Add metadata
        data_with_meta = data.copy()
        if "_meta" not in data_with_meta:
            data_with_meta["_meta"] = {}
            
        data_with_meta["_meta"]["created_at"] = datetime.now().isoformat()
        data_with_meta["_meta"]["updated_at"] = datetime.now().isoformat()
        
        # Encrypt data
        encrypted_data = self.encryption.encrypt(data_with_meta)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if record exists
            cursor.execute(
                "SELECT 1 FROM user_data WHERE user_id = ? AND data_type = ? AND data_id = ?",
                (user_id, data_type, data_id)
            )
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing record
                cursor.execute(
                    """UPDATE user_data SET 
                    encrypted_data = ?, 
                    updated_at = ? 
                    WHERE user_id = ? AND data_type = ? AND data_id = ?""",
                    (
                        encrypted_data,
                        datetime.now().isoformat(),
                        user_id,
                        data_type,
                        data_id
                    )
                )
                action = "update"
            else:
                # Insert new record
                cursor.execute(
                    """INSERT INTO user_data 
                    (user_id, data_type, data_id, encrypted_data, created_at, updated_at, metadata) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        data_type,
                        data_id,
                        encrypted_data,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps({"source": "api"})
                    )
                )
                action = "create"
            
            conn.commit()
            conn.close()
            
            # Log the access
            self.audit.log_access(
                user_id=user_id,
                data_type=data_type,
                resource_id=data_id,
                action=action,
                client_info=client_info
            )
            
            return data_id
        except Exception as e:
            logger.error(f"Failed to store data: {str(e)}")
            raise
    
    def retrieve_data(self, user_id: str, data_type: str, data_id: str, 
                    client_info: Dict = None) -> Optional[Dict]:
        """
        Retrieve and decrypt user data
        
        Args:
            user_id: User ID
            data_type: Type of data
            data_id: Data ID
            client_info: Client information for audit log
            
        Returns:
            Decrypted data or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT encrypted_data, created_at FROM user_data WHERE user_id = ? AND data_type = ? AND data_id = ?",
                (user_id, data_type, data_id)
            )
            result = cursor.fetchone()
            
            conn.close()
            
            if not result:
                return None
                
            encrypted_data, created_at = result
            
            # Check if data should be anonymized
            should_anonymize = self.retention.should_anonymize(data_type, created_at)
            
            # Decrypt data
            decrypted_data = json.loads(self.encryption.decrypt(encrypted_data))
            
            # Anonymize if needed
            if should_anonymize:
                decrypted_data = self.retention.anonymize_data(decrypted_data, data_type)
            
            # Log the access
            self.audit.log_access(
                user_id=user_id,
                data_type=data_type,
                resource_id=data_id,
                action="read",
                client_info=client_info
            )
            
            return decrypted_data
        except Exception as e:
            logger.error(f"Failed to retrieve data: {str(e)}")
            return None
    
    def delete_data(self, user_id: str, data_type: str = None, data_id: str = None, 
                  client_info: Dict = None) -> bool:
        """
        Delete user data with audit logging
        
        Args:
            user_id: User ID
            data_type: Type of data (if None, all types for user are deleted)
            data_id: Data ID (if None, all IDs of specified type are deleted)
            client_info: Client information for audit log
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type and data_id:
                # Delete specific record
                cursor.execute(
                    "DELETE FROM user_data WHERE user_id = ? AND data_type = ? AND data_id = ?",
                    (user_id, data_type, data_id)
                )
                resource_id = f"{data_type}:{data_id}"
                
            elif data_type:
                # Delete all records of specific type
                cursor.execute(
                    "DELETE FROM user_data WHERE user_id = ? AND data_type = ?",
                    (user_id, data_type)
                )
                resource_id = f"{data_type}:all"
                
            else:
                # Delete all user data
                cursor.execute(
                    "DELETE FROM user_data WHERE user_id = ?",
                    (user_id,)
                )
                resource_id = "all_data"
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            # Log the deletion
            self.audit.log_access(
                user_id=user_id,
                data_type=data_type or "all",
                resource_id=resource_id,
                action="delete",
                details=f"Deleted {deleted_count} records",
                client_info=client_info
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete data: {str(e)}")
            return False
    
    def request_data_deletion(self, user_id: str, request_type: str = "all_data", 
                            client_info: Dict = None) -> str:
        """
        Create a data deletion request for compliance with privacy regulations
        
        Args:
            user_id: User ID
            request_type: Type of deletion request
            client_info: Client information for audit log
            
        Returns:
            Request ID
        """
        request_id = str(uuid.uuid4())
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """INSERT INTO deletion_requests 
                (request_id, user_id, request_type, status, created_at) 
                VALUES (?, ?, ?, ?, ?)""",
                (
                    request_id,
                    user_id,
                    request_type,
                    "pending",
                    datetime.now().isoformat()
                )
            )
            
            conn.commit()
            conn.close()
            
            # Log the request
            self.audit.log_access(
                user_id=user_id,
                data_type="deletion_request",
                resource_id=request_id,
                action="create",
                details=f"Requested deletion of {request_type}",
                client_info=client_info
            )
            
            return request_id
        except Exception as e:
            logger.error(f"Failed to create deletion request: {str(e)}")
            raise
    
    def get_user_data(self, user_id: str, data_type: str = None, 
                    limit: int = 100, client_info: Dict = None) -> List[Dict]:
        """
        Get all data for a user (for GDPR compliance)
        
        Args:
            user_id: User ID
            data_type: Optional filter by data type
            limit: Maximum number of records to return
            client_info: Client information for audit log
            
        Returns:
            List of user data objects
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if data_type:
                cursor.execute(
                    """SELECT data_type, data_id, encrypted_data, created_at, updated_at 
                    FROM user_data 
                    WHERE user_id = ? AND data_type = ? 
                    ORDER BY updated_at DESC LIMIT ?""",
                    (user_id, data_type, limit)
                )
            else:
                cursor.execute(
                    """SELECT data_type, data_id, encrypted_data, created_at, updated_at 
                    FROM user_data 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC LIMIT ?""",
                    (user_id, limit)
                )
                
            rows = cursor.fetchall()
            conn.close()
            
            result = []
            for row in rows:
                data_type, data_id, encrypted_data, created_at, updated_at = row
                
                # Check if data should be anonymized
                should_anonymize = self.retention.should_anonymize(data_type, created_at)
                
                # Decrypt data
                try:
                    decrypted_data = json.loads(self.encryption.decrypt(encrypted_data))
                    
                    # Anonymize if needed
                    if should_anonymize:
                        decrypted_data = self.retention.anonymize_data(decrypted_data, data_type)
                    
                    # Add metadata if not present
                    if "_meta" not in decrypted_data:
                        decrypted_data["_meta"] = {}
                        
                    decrypted_data["_meta"]["data_id"] = data_id
                    decrypted_data["_meta"]["data_type"] = data_type
                    decrypted_data["_meta"]["created_at"] = created_at
                    decrypted_data["_meta"]["updated_at"] = updated_at
                    
                    result.append(decrypted_data)
                except Exception as e:
                    logger.error(f"Failed to decrypt data {data_id}: {str(e)}")
                    # Add error placeholder
                    result.append({
                        "_meta": {
                            "data_id": data_id,
                            "data_type": data_type,
                            "created_at": created_at,
                            "updated_at": updated_at,
                            "error": "Decryption failed"
                        }
                    })
            
            # Log the access
            self.audit.log_access(
                user_id=user_id,
                data_type=data_type or "all",
                resource_id="bulk_export",
                action="read",
                details=f"Retrieved {len(result)} records",
                client_info=client_info
            )
            
            return result
        except Exception as e:
            logger.error(f"Failed to retrieve user data: {str(e)}")
            return []
    
    def process_deletion_requests(self, max_requests: int = 100) -> int:
        """
        Process pending deletion requests
        
        Args:
            max_requests: Maximum number of requests to process
            
        Returns:
            Number of requests processed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get pending requests
            cursor.execute(
                """SELECT request_id, user_id, request_type 
                FROM deletion_requests 
                WHERE status = 'pending' 
                ORDER BY created_at ASC LIMIT ?""",
                (max_requests,)
            )
            
            pending_requests = cursor.fetchall()
            processed_count = 0
            
            for request_id, user_id, request_type in pending_requests:
                # Process the deletion
                if request_type == "all_data":
                    success = self.delete_data(user_id)
                else:
                    # Specific data type
                    success = self.delete_data(user_id, data_type=request_type)
                
                if success:
                    # Update request status
                    cursor.execute(
                        """UPDATE deletion_requests 
                        SET status = 'completed', completed_at = ? 
                        WHERE request_id = ?""",
                        (datetime.now().isoformat(), request_id)
                    )
                    processed_count += 1
                else:
                    # Mark as failed
                    cursor.execute(
                        """UPDATE deletion_requests 
                        SET status = 'failed', completed_at = ? 
                        WHERE request_id = ?""",
                        (datetime.now().isoformat(), request_id)
                    )
            
            conn.commit()
            conn.close()
            
            return processed_count
        except Exception as e:
            logger.error(f"Failed to process deletion requests: {str(e)}")
            return 0
    
    def run_retention_cleanup(self) -> int:
        """
        Clean up data based on retention policy
        
        Returns:
            Number of records deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all records
            cursor.execute("SELECT user_id, data_type, data_id, created_at FROM user_data")
            records = cursor.fetchall()
            
            deleted_count = 0
            for user_id, data_type, data_id, created_at in records:
                # Check if data should be deleted
                if self.retention.should_delete(data_type, created_at):
                    cursor.execute(
                        "DELETE FROM user_data WHERE user_id = ? AND data_type = ? AND data_id = ?",
                        (user_id, data_type, data_id)
                    )
                    deleted_count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Retention cleanup: deleted {deleted_count} records")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to run retention cleanup: {str(e)}")
            return 0
    
    def _check_maintenance(self):
        """Check and run maintenance tasks if needed"""
        current_time = time.time()
        if current_time - self._last_maintenance > self._maintenance_interval:
            try:
                # Run maintenance tasks
                self.process_deletion_requests()
                self.run_retention_cleanup()
                self._last_maintenance = current_time
            except Exception as e:
                logger.error(f"Maintenance error: {str(e)}")
    
    def export_keys(self) -> Dict:
        """
        Export encryption keys for backup
        
        Returns:
            Dict with encryption keys
        """
        return self.encryption.export_keys()
    
    def get_data_access_report(self, user_id: str, 
                             start_date: datetime = None, 
                             end_date: datetime = None) -> Dict:
        """
        Generate a data access report for a user (for compliance)
        
        Args:
            user_id: User ID
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Dict with access report data
        """
        # Get access logs
        access_logs = self.audit.get_user_access_logs(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate statistics
        total_accesses = len(access_logs)
        access_by_type = {}
        access_by_action = {}
        
        for log in access_logs:
            data_type = log.get("data_type", "unknown")
            action = log.get("action", "unknown")
            
            access_by_type[data_type] = access_by_type.get(data_type, 0) + 1
            access_by_action[action] = access_by_action.get(action, 0) + 1
        
        # Structure the report
        report = {
            "user_id": user_id,
            "period": {
                "start": start_date.isoformat() if start_date else "all",
                "end": end_date.isoformat() if end_date else datetime.now().isoformat()
            },
            "total_accesses": total_accesses,
            "access_by_type": access_by_type,
            "access_by_action": access_by_action,
            "access_logs": access_logs[:100]  # Limit to 100 entries
        }
        
        return report 