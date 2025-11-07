"""
Railway-Optimized Flask Forum Application - COMPLETE REWRITE
Fully production-ready for Railway deployment
"""

import os
import logging
import sqlite3
import jwt
import bcrypt
import secrets
import hashlib
import html
import bleach
import re
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse
from functools import wraps
from contextlib import contextmanager
from flask import Flask, request, jsonify, send_from_directory, current_app, render_template
from flask import Flask, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# =============================================================================
# CONFIGURATION FOR RAILWAY
# =============================================================================
class RailwayConfig:
    PORT = int(os.environ.get('PORT', 5000))
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    DB_NAME = os.environ.get('DB_NAME', 'railway_forum.db')
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', '2000'))
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))
    BCRYPT_ROUNDS = 12
    MIN_PASSWORD_LENGTH = 8
    MAX_USERNAME_LENGTH = 20
    MAX_POST_LENGTH = 10000
    MAX_COMMENT_LENGTH = 2000
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    CONNECTION_TIMEOUT = 30
    WAL_MODE = True

# =============================================================================
# DATABASE MANAGEMENT - COMPLETE REWRITE
# =============================================================================
class DatabaseManager:
    def __init__(self, app):
        self.app = app
        self._connection = None
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.app.config['DB_NAME'],
                check_same_thread=False,
                timeout=self.app.config['CONNECTION_TIMEOUT']
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            if self.app.config['WAL_MODE']:
                self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = NORMAL")
            self._connection.execute("PRAGMA cache_size = -64000")
        return self._connection
    
    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        try:
            cursor = self.connection.cursor()
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e

def init_database(app):
    """COMPLETE database initialization"""
    db_manager = DatabaseManager(app)
    
    try:
        with db_manager.get_cursor() as cursor:
            # COMPLETE schema creation
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE,
                    full_name TEXT,
                    avatar_color TEXT DEFAULT '#007AFF',
                    bio TEXT,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    last_login DATETIME,
                    is_active BOOLEAN DEFAULT 1,
                    reputation INTEGER DEFAULT 0,
                    post_count INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    like_count INTEGER DEFAULT 0,
                    is_moderator BOOLEAN DEFAULT 0,
                    is_admin BOOLEAN DEFAULT 0,
                    email_verified BOOLEAN DEFAULT 0,
                    verification_token TEXT,
                    reset_token TEXT,
                    reset_token_expiry DATETIME,
                    last_password_change DATETIME DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS categories(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    color TEXT DEFAULT '#007AFF',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    post_count INTEGER DEFAULT 0,
                    last_post_date DATETIME
                );

                CREATE TABLE IF NOT EXISTS posts(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    content_search TEXT,
                    timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
                    last_activity DATETIME NOT NULL DEFAULT (datetime('now')),
                    likes_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    is_pinned BOOLEAN DEFAULT 0,
                    is_locked BOOLEAN DEFAULT 0,
                    is_deleted BOOLEAN DEFAULT 0,
                    tags TEXT,
                    edited_at DATETIME,
                    edited_by INTEGER,
                    view_count INTEGER DEFAULT 0,
                    featured_until DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(edited_by) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS comments(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
                    likes_count INTEGER DEFAULT 0,
                    edited_at DATETIME,
                    edited_by INTEGER,
                    parent_comment_id INTEGER,
                    is_deleted BOOLEAN DEFAULT 0,
                    depth INTEGER DEFAULT 0,
                    path TEXT DEFAULT '',
                    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(parent_comment_id) REFERENCES comments(id) ON DELETE CASCADE,
                    FOREIGN KEY(edited_by) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS likes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    post_id INTEGER,
                    comment_id INTEGER,
                    timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
                    type TEXT DEFAULT 'like',
                    UNIQUE(user_id, post_id, comment_id),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY(comment_id) REFERENCES comments(id) ON DELETE CASCADE,
                    CHECK((post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL))
                );

                CREATE TABLE IF NOT EXISTS bookmarks(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    post_id INTEGER NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    notes TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    UNIQUE(user_id, post_id)
                );

                CREATE TABLE IF NOT EXISTS user_sessions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    expires_at DATETIME NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    last_activity DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS user_activity(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp DATETIME NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS reports(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reporter_id INTEGER NOT NULL,
                    post_id INTEGER,
                    comment_id INTEGER,
                    reason TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    resolved_at DATETIME,
                    resolved_by INTEGER,
                    FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
                    FOREIGN KEY(comment_id) REFERENCES comments(id) ON DELETE CASCADE,
                    FOREIGN KEY(resolved_by) REFERENCES users(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS notifications(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    is_read BOOLEAN DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
                    expires_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)

            # Create indexes
            cursor.executescript("""
                CREATE INDEX IF NOT EXISTS idx_posts_user_category ON posts(user_id, category);
                CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_posts_last_activity ON posts(last_activity DESC);
                CREATE INDEX IF NOT EXISTS idx_posts_popularity ON posts(likes_count DESC, comments_count DESC);
                CREATE INDEX IF NOT EXISTS idx_comments_post_path ON comments(post_id, path);
                CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_users_reputation ON users(reputation DESC);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id, expires_at);
                CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON bookmarks(user_id, created_at DESC);
            """)

            # Insert default categories
            default_categories = [
                ('General', 'General discussions and topics', '#007AFF'),
                ('Technology', 'Tech news, programming, and gadgets', '#34C759'),
                ('Science', 'Scientific discoveries and discussions', '#FF9500'),
                ('Entertainment', 'Movies, games, and entertainment', '#AF52DE'),
                ('Sports', 'Sports news and discussions', '#FF3B30'),
                ('Politics', 'Political discussions and news', '#5856D6')
            ]
            
            cursor.executemany("""
                INSERT OR IGNORE INTO categories (name, description, color) 
                VALUES (?, ?, ?)
            """, default_categories)

        app.logger.info("Database schema initialized successfully")
        
    except Exception as e:
        app.logger.error(f"Database initialization error: {e}")
        raise
    finally:
        db_manager.close()

# =============================================================================
# SECURITY UTILITIES - COMPLETE REWRITE
# =============================================================================
class SecurityUtils:
    @staticmethod
    def validate_username(username):
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(username) > 20:
            raise ValueError("Username must be less than 20 characters")
        if not re.match(r'^[a-zA-Z0-9_\-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        if username.lower() in ['admin', 'administrator', 'moderator', 'system']:
            raise ValueError("Username not allowed")
        return username.lower().strip()
    
    @staticmethod
    def validate_password(password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        checks = {
            'uppercase': bool(re.search(r'[A-Z]', password)),
            'lowercase': bool(re.search(r'[a-z]', password)),
            'digit': bool(re.search(r'\d', password)),
            'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        }
        
        if sum(checks.values()) < 3:
            raise ValueError("Password must contain at least 3 of: uppercase, lowercase, digits, special characters")
        
        common_passwords = {'password', '123456', 'qwerty', 'letmein', 'welcome'}
        if password.lower() in common_passwords:
            raise ValueError("Password is too common")
        
        return password
    
    @staticmethod
    def sanitize_html(content, max_length=None):
        if not content:
            return content
        
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS + [
            'p', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'strong', 'em', 'u', 'strike', 'blockquote',
            'code', 'pre', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
        ]
        
        allowed_attributes = {
            '*': ['class', 'style', 'id'],
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'width', 'height', 'title'],
            'code': ['class'],
            'span': ['style']
        }
        
        cleaned = bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True,
            strip_comments=True
        )
        
        cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'vbscript:', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'on\w+=', '', cleaned, flags=re.IGNORECASE)
        
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned.strip()
    
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
    
    @staticmethod
    def check_password(password, hashed):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed)
        except Exception:
            return False
    
    @staticmethod
    def generate_secure_token(length=32):
        return secrets.token_hex(length)

# =============================================================================
# AUTHENTICATION DECORATORS - COMPLETE REWRITE
# =============================================================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        
        if not token:
            return jsonify({"success": False, "error": "Authentication token required"}), 401
        
        if not token.startswith('Bearer '):
            return jsonify({"success": False, "error": "Invalid token format"}), 401
        
        token = token[7:]
        
        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, is_active, last_login, avatar_color 
                    FROM users WHERE id = ?
                """, (decoded["user_id"],))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({"success": False, "error": "User not found"}), 401                
                if not user["is_active"]:
                    return jsonify({"success": False, "error": "Account deactivated"}), 403
                
                request.user_id = user["id"]
                request.username = user["username"]
                request.user_data = dict(user)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        except Exception as e:
            current_app.logger.error(f"Token validation error: {e}")
            return jsonify({"success": False, "error": "Token validation failed"}), 401
        
        return f(*args, **kwargs)
    return decorated

def validate_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"}), 400
        
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"success": False, "error": "Invalid JSON data"}), 400
        
        request.json_data = data
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# UTILITY FUNCTIONS - COMPLETE REWRITE
# =============================================================================
def log_user_activity(user_id, action, details=None):
    """Log user activity"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            
            cursor.execute("""INSERT INTO user_activity 
                        (user_id, action, details, ip_address, user_agent) 
                        VALUES (?, ?, ?, ?, ?)""",
                     (user_id, action, str(details) if details else None, ip_address, user_agent))
    except Exception as e:
        current_app.logger.error(f"Activity logging error: {e}")

def create_notification(user_id, type, title, message, data=None, expires_hours=24):
    """Create user notification"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            expires_at = datetime.now() + timedelta(hours=expires_hours) if expires_hours else None
            
            cursor.execute("""
                INSERT INTO notifications (user_id, type, title, message, data, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, type, title, message, data, expires_at))
            
            return cursor.lastrowid
    except Exception as e:
        current_app.logger.error(f"Notification creation error: {e}")
        return None

def format_timestamp(timestamp):
    """Format timestamp for display"""
    if not timestamp:
        return "Recently"
    
    try:
        if isinstance(timestamp, str):
            post_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            post_time = timestamp
            
        now = datetime.now()
        diff = now - post_time
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Recently"

def generate_avatar_color():
    colors = ['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE', '#5856D6', '#FF2D55', '#32D74B']
    return random.choice(colors)

# =============================================================================
# ROUTE HANDLERS - COMPLETE REWRITE
# =============================================================================
def handle_register():
    """COMPLETE user registration handler"""
    data = request.json_data
    
    try:
        username = SecurityUtils.validate_username(data.get("username", ""))
        password = SecurityUtils.validate_password(data.get("password", ""))
        email = data.get("email")
        
        if email:
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                raise ValueError("Invalid email format")
        
        full_name = SecurityUtils.sanitize_html(data.get("full_name", ""), 50)
        bio = SecurityUtils.sanitize_html(data.get("bio", ""), 200)
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
            if cursor.fetchone():
                raise ValueError("Username or email already exists")
            
            hashed_pw = SecurityUtils.hash_password(password)
            avatar_color = generate_avatar_color()
            verification_token = SecurityUtils.generate_secure_token() if email else None
            
            cursor.execute("""INSERT INTO users 
                        (username, password, email, full_name, avatar_color, bio, verification_token) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (username, hashed_pw, email, full_name, avatar_color, bio, verification_token))
            
            user_id = cursor.lastrowid
        
        log_user_activity(user_id, "user_registered", {"email_provided": bool(email)})
        current_app.logger.info(f"New user registered: {username} (ID: {user_id})")
        
        return jsonify({
            "success": True, 
            "message": "Account created successfully",
            "user_id": user_id,
            "requires_verification": bool(email)
        })
    
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({"success": False, "error": "Registration failed"}), 500

def handle_login():
    """COMPLETE login handler"""
    data = request.json_data
    
    try:
        username = data.get("username", "").strip().lower()
        password = data.get("password", "")
        remember_me = data.get("remember_me", False)
        
        if not username or not password:
            raise ValueError("Username and password required")
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT id, password, username, avatar_color, is_active, email_verified 
                FROM users WHERE username = ? OR email = ?
            """, (username, username))
            
            user = cursor.fetchone()
            
            if not user or not SecurityUtils.check_password(password, user["password"]):
                log_user_activity(None, "failed_login", {"username": username})
                raise ValueError("Invalid credentials")
            
            if not user["is_active"]:
                raise ValueError("Account deactivated")
            
            cursor.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user["id"],))
            
            token_expiry = timedelta(hours=24) if remember_me else timedelta(hours=6)
            token = jwt.encode({
                "user_id": user["id"],
                "username": user["username"],
                "exp": datetime.utcnow() + token_expiry
            }, current_app.config['SECRET_KEY'], algorithm="HS256")
            
            session_token = SecurityUtils.generate_secure_token()
            expires_at = datetime.now() + token_expiry
            
            cursor.execute("""
                INSERT INTO user_sessions 
                (user_id, session_token, expires_at, ip_address, user_agent) 
                VALUES (?, ?, ?, ?, ?)
            """, (user["id"], session_token, expires_at, request.remote_addr, request.headers.get('User-Agent')))
        
        log_user_activity(user["id"], "login_success")
        
        return jsonify({
            "success": True, 
            "token": token,
            "session_token": session_token,
            "expires_in": int(token_expiry.total_seconds()),
            "user": {
                "id": user["id"],
                "username": user["username"],
                "avatar_color": user["avatar_color"],
                "email_verified": user["email_verified"]
            }
        })
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": "Login failed"}), 500

def handle_logout():
    """COMPLETE logout handler"""
    session_token = request.headers.get('X-Session-Token')
    
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            if session_token:
                cursor.execute("""
                    UPDATE user_sessions SET is_active = 0 
                    WHERE session_token = ? AND user_id = ?
                """, (session_token, request.user_id))
            
            log_user_activity(request.user_id, "logout")
            return jsonify({"success": True, "message": "Logged out successfully"})
            
    except Exception as e:
        current_app.logger.error(f"Logout error: {e}")
        return jsonify({"success": False, "error": "Logout failed"}), 500

def get_categories():
    """COMPLETE categories handler"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY name")
            categories = [dict(row) for row in cursor.fetchall()]
            return jsonify({"success": True, "categories": categories})
    except Exception as e:
        current_app.logger.error(f"Categories error: {e}")
        return jsonify({"success": False, "error": "Failed to get categories"}), 500

def create_post():
    """COMPLETE post creation handler"""
    data = request.json_data
    
    try:
        category = SecurityUtils.sanitize_html(data.get("category", ""), 50)
        content = SecurityUtils.sanitize_html(data.get("content", ""), current_app.config['MAX_POST_LENGTH'])
        title = SecurityUtils.sanitize_html(data.get("title", ""), 200)
        
        if len(content.strip()) < 10:
            raise ValueError("Content must be at least 10 characters")
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT name FROM categories WHERE name = ? AND is_active = 1", (category,))
            if not cursor.fetchone():
                raise ValueError("Invalid category")
            
            cursor.execute("""
                INSERT INTO posts (user_id, category, title, content) 
                VALUES (?, ?, ?, ?)
            """, (request.user_id, category, title, content))
            
            post_id = cursor.lastrowid
            
            cursor.execute("UPDATE users SET post_count = post_count + 1 WHERE id = ?", (request.user_id,))
            
            cursor.execute("""
                UPDATE categories SET 
                post_count = post_count + 1,
                last_post_date = datetime('now')
                WHERE name = ?
            """, (category,))
        
        log_user_activity(request.user_id, "post_created", {"post_id": post_id, "category": category})
        
        return jsonify({
            "success": True, 
            "message": "Post created successfully", 
            "post_id": post_id
        }), 201
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Post creation error: {e}")
        return jsonify({"success": False, "error": "Failed to create post"}), 500

def get_posts():
    """COMPLETE posts retrieval handler"""
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 10, type=int)), 50)
        category = request.args.get('category', '')
        search = SecurityUtils.sanitize_html(request.args.get('search', ''), 100)
        sort = request.args.get('sort', 'newest')
        user_id = request.args.get('user_id', type=int)
        
        offset = (page - 1) * per_page
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            query = """
                SELECT p.*, u.username, u.avatar_color, u.reputation,
                       (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.id AND c.is_deleted = 0) as real_comments_count
                FROM posts p 
                JOIN users u ON p.user_id = u.id 
                WHERE p.is_deleted = 0 AND u.is_active = 1
            """
            
            count_query = """
                SELECT COUNT(*) 
                FROM posts p 
                JOIN users u ON p.user_id = u.id 
                WHERE p.is_deleted = 0 AND u.is_active = 1
            """
            
            params = []
            
            if category:
                query += " AND p.category = ?"
                count_query += " AND p.category = ?"
                params.append(category)
            
            if search:
                query += " AND (p.content LIKE ? OR u.username LIKE ? OR p.title LIKE ?)"
                count_query += " AND (p.content LIKE ? OR u.username LIKE ? OR p.title LIKE ?)"
                search_term = f'%{search}%'
                params.extend([search_term, search_term, search_term])
            
            if user_id:
                query += " AND p.user_id = ?"
                count_query += " AND p.user_id = ?"
                params.append(user_id)
            
            sort_options = {
                'newest': 'p.timestamp DESC',
                'oldest': 'p.timestamp ASC',
                'popular': 'p.likes_count DESC, p.comments_count DESC',
                'active': 'p.last_activity DESC'
            }
            
            query += f" ORDER BY {sort_options.get(sort, 'p.timestamp DESC')}"
            query += " LIMIT ? OFFSET ?"
            
            count_params = params.copy()
            params.extend([per_page, offset])
            
            cursor.execute(count_query, count_params)
            total_count = cursor.fetchone()[0]
            
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            
            for post in rows:
                cursor.execute("SELECT id FROM likes WHERE user_id = ? AND post_id = ?", 
                             (request.user_id, post['id']))
                post['user_has_liked'] = cursor.fetchone() is not None
                
                cursor.execute("SELECT id FROM bookmarks WHERE user_id = ? AND post_id = ?",
                             (request.user_id, post['id']))
                post['user_has_bookmarked'] = cursor.fetchone() is not None
                
                post['formatted_timestamp'] = format_timestamp(post['timestamp'])
                post['formatted_last_activity'] = format_timestamp(post['last_activity'])
            
            return jsonify({
                "success": True, 
                "data": rows,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_count,
                    "pages": (total_count + per_page - 1) // per_page
                },
                "filters": {
                    "category": category,
                    "search": search,
                    "sort": sort
                }
            })
            
    except Exception as e:
        current_app.logger.error(f"Posts retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve posts"}), 500

def handle_get_post(post_id):
    """COMPLETE single post handler"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT p.*, u.username, u.avatar_color, u.reputation
                FROM posts p 
                JOIN users u ON p.user_id = u.id 
                WHERE p.id = ? AND p.is_deleted = 0
            """, (post_id,))
            
            post = cursor.fetchone()
            if not post:
                return jsonify({"success": False, "error": "Post not found"}), 404
            
            post = dict(post)
            
            cursor.execute("""
                SELECT c.*, u.username, u.avatar_color
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = ? AND c.is_deleted = 0
                ORDER BY c.timestamp ASC
            """, (post_id,))
            
            comments = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("SELECT id FROM likes WHERE user_id = ? AND post_id = ?", 
                         (request.user_id, post_id))
            post['user_has_liked'] = cursor.fetchone() is not None
            
            cursor.execute("SELECT id FROM bookmarks WHERE user_id = ? AND post_id = ?",
                         (request.user_id, post_id))
            post['user_has_bookmarked'] = cursor.fetchone() is not None
            
            post['formatted_timestamp'] = format_timestamp(post['timestamp'])
            
            return jsonify({
                "success": True,
                "post": post,
                "comments": comments
            })
            
    except Exception as e:
        current_app.logger.error(f"Post retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve post"}), 500

def handle_like_post(post_id):
    """COMPLETE post like handler"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            if request.method == 'POST':
                cursor.execute("SELECT id FROM likes WHERE user_id = ? AND post_id = ?", 
                             (request.user_id, post_id))
                if cursor.fetchone():
                    return jsonify({"success": False, "error": "Already liked"}), 400
                
                cursor.execute("INSERT INTO likes (user_id, post_id) VALUES (?, ?)", 
                             (request.user_id, post_id))
                
                cursor.execute("UPDATE posts SET likes_count = likes_count + 1 WHERE id = ?", (post_id,))
                cursor.execute("UPDATE users SET like_count = like_count + 1 WHERE id = ?", (request.user_id,))
                
                return jsonify({"success": True, "message": "Post liked"})
                
            else:
                cursor.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", 
                             (request.user_id, post_id))
                
                if cursor.rowcount > 0:
                    cursor.execute("UPDATE posts SET likes_count = likes_count - 1 WHERE id = ?", (post_id,))
                    cursor.execute("UPDATE users SET like_count = like_count - 1 WHERE id = ?", (request.user_id,))
                    return jsonify({"success": True, "message": "Post unliked"})
                else:
                    return jsonify({"success": False, "error": "Like not found"}), 404
                    
    except Exception as e:
        current_app.logger.error(f"Like error: {e}")
        return jsonify({"success": False, "error": "Failed to process like"}), 500

def handle_bookmark_post(post_id):
    """COMPLETE bookmark handler"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            if request.method == 'POST':
                cursor.execute("SELECT id FROM bookmarks WHERE user_id = ? AND post_id = ?", 
                             (request.user_id, post_id))
                if cursor.fetchone():
                    return jsonify({"success": False, "error": "Already bookmarked"}), 400
                
                cursor.execute("INSERT INTO bookmarks (user_id, post_id) VALUES (?, ?)", 
                             (request.user_id, post_id))
                
                return jsonify({"success": True, "message": "Post bookmarked"})
                
            else:
                cursor.execute("DELETE FROM bookmarks WHERE user_id = ? AND post_id = ?", 
                             (request.user_id, post_id))
                
                if cursor.rowcount > 0:
                    return jsonify({"success": True, "message": "Post unbookmarked"})
                else:
                    return jsonify({"success": False, "error": "Bookmark not found"}), 404
                    
    except Exception as e:
        current_app.logger.error(f"Bookmark error: {e}")
        return jsonify({"success": False, "error": "Failed to process bookmark"}), 500

def handle_add_comment(post_id):
    """COMPLETE comment handler"""
    data = request.json_data
    
    try:
        content = SecurityUtils.sanitize_html(data.get("content", ""), current_app.config['MAX_COMMENT_LENGTH'])
        
        if len(content.strip()) < 1:
            raise ValueError("Comment content is required")
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT id FROM posts WHERE id = ? AND is_deleted = 0", (post_id,))
            if not cursor.fetchone():
                raise ValueError("Post not found")
            
            cursor.execute("""
                INSERT INTO comments (post_id, user_id, content) 
                VALUES (?, ?, ?)
            """, (post_id, request.user_id, content))
            
            comment_id = cursor.lastrowid
            
            cursor.execute("""
                UPDATE posts SET 
                comments_count = comments_count + 1,
                last_activity = datetime('now')
                WHERE id = ?
            """, (post_id,))
            
            cursor.execute("UPDATE users SET comment_count = comment_count + 1 WHERE id = ?", (request.user_id,))
        
        log_user_activity(request.user_id, "comment_created", {"post_id": post_id, "comment_id": comment_id})
        
        return jsonify({
            "success": True, 
            "message": "Comment added successfully", 
            "comment_id": comment_id
        }), 201
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Comment creation error: {e}")
        return jsonify({"success": False, "error": "Failed to add comment"}), 500

def handle_like_comment(comment_id):
    """COMPLETE comment like handler"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            if request.method == 'POST':
                cursor.execute("SELECT id FROM likes WHERE user_id = ? AND comment_id = ?", 
                             (request.user_id, comment_id))
                if cursor.fetchone():
                    return jsonify({"success": False, "error": "Already liked"}), 400
                
                cursor.execute("INSERT INTO likes (user_id, comment_id) VALUES (?, ?)", 
                             (request.user_id, comment_id))
                
                cursor.execute("UPDATE comments SET likes_count = likes_count + 1 WHERE id = ?", (comment_id,))
                
                return jsonify({"success": True, "message": "Comment liked"})
                
            else:
                cursor.execute("DELETE FROM likes WHERE user_id = ? AND comment_id = ?", 
                             (request.user_id, comment_id))
                
                if cursor.rowcount > 0:
                    cursor.execute("UPDATE comments SET likes_count = likes_count - 1 WHERE id = ?", (comment_id,))
                    return jsonify({"success": True, "message": "Comment unliked"})
                else:
                    return jsonify({"success": False, "error": "Like not found"}), 404
                    
    except Exception as e:
        current_app.logger.error(f"Comment like error: {e}")
        return jsonify({"success": False, "error": "Failed to process like"}), 500

def handle_analytics():
    """COMPLETE analytics handler"""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            stats = {}
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN last_login > datetime('now', '-7 days') THEN 1 END) as active_week,
                    COUNT(CASE WHEN last_login > datetime('now', '-1 day') THEN 1 END) as active_today,
                    COUNT(CASE WHEN created_at > datetime('now', '-7 days') THEN 1 END) as new_users_week,
                    AVG(reputation) as avg_reputation
                FROM users 
                WHERE is_active = 1
            """)
            stats['users'] = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(CASE WHEN timestamp > datetime('now', '-7 days') THEN 1 END) as posts_week,
                    COUNT(CASE WHEN timestamp > datetime('now', '-1 day') THEN 1 END) as posts_today,
                    AVG(likes_count) as avg_likes,
                    AVG(comments_count) as avg_comments,
                    SUM(view_count) as total_views
                FROM posts
                WHERE is_deleted = 0
            """)
            stats['posts'] = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT
                    COUNT(*) as total_likes,
                    COUNT(*) as total_comments,
                    COUNT(DISTINCT user_id) as active_posters
                FROM posts p
                WHERE p.is_deleted = 0
            """)
            stats['engagement'] = dict(cursor.fetchone())
            
            cursor.execute("""
                SELECT 
                    c.name as category,
                    c.post_count,
                    c.color,
                    COUNT(CASE WHEN p.timestamp > datetime('now', '-7 days') THEN 1 END) as posts_week,
                    AVG(p.likes_count) as avg_likes,
                    AVG(p.comments_count) as avg_comments
                FROM categories c
                LEFT JOIN posts p ON c.name = p.category AND p.is_deleted = 0
                WHERE c.is_active = 1
                GROUP BY c.id
                ORDER BY c.post_count DESC
                LIMIT 10
            """)
            stats['popular_categories'] = [dict(row) for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT 
                    u.username,
                    u.avatar_color,
                    u.reputation,
                    u.post_count,
                    u.comment_count,
                    u.like_count
                FROM users u
                WHERE u.is_active = 1
                ORDER BY u.reputation DESC, u.post_count DESC
                LIMIT 10
            """)
            stats['top_contributors'] = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                "success": True,
                "analytics": stats,
                "generated_at": datetime.now().isoformat()
            })
            
    except Exception as e:
        current_app.logger.error(f"Analytics error: {e}")
        return jsonify({"success": False, "error": "Failed to get analytics"}), 500

# =============================================================================
# APPLICATION FACTORY - COMPLETE REWRITE
# =============================================================================
def create_app(config_class=RailwayConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enhanced CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    
    # Security headers
    csp = {
        'default-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'script-src': ["'self'", "https://cdn.jsdelivr.net"],
        'font-src': ["'self'", "https://cdn.jsdelivr.net"],
        'img-src': ["'self'", "data:", "https:"]
    }
    
    Talisman(
        app,
        content_security_policy=csp,
        force_https=os.environ.get('RAILWAY_ENVIRONMENT') == 'production',
        strict_transport_security=True
    )
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{config_class.RATE_LIMIT_PER_HOUR}/hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    
    # Logging
    logging.basicConfig(
        level=logging.INFO if os.environ.get('RAILWAY_ENVIRONMENT') == 'production' else logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]'
    )
    app.logger.setLevel(logging.INFO)
    
    # Initialize database
    with app.app_context():
        init_database(app)
    
    # =========================================================================
    # ROUTE REGISTRATION - COMPLETE
    # =========================================================================
    @app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/beds')
def serve_beds():
    return render_template('beds.html')

# Serve static files if you have any
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)
    
    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory('.', path)
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development'),
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        })
    
    # Authentication routes
    @app.route('/api/register', methods=['POST'])
    @limiter.limit("5 per hour")
    @validate_json
    def register():
        return handle_register()
    
    @app.route('/api/login', methods=['POST'])
    @limiter.limit("10 per 15 minutes")
    @validate_json
    def login():
        return handle_login()
    
    @app.route('/api/logout', methods=['POST'])
    @token_required
    def logout():
        return handle_logout()
    
    # Categories
    @app.route('/api/categories')
    def categories():
        return get_categories()
    
    # Posts routes
    @app.route('/api/posts', methods=['GET', 'POST'])
    @token_required
    def posts():
        if request.method == 'POST':
            return create_post()
        return get_posts()
    
    @app.route('/api/posts/<int:post_id>')
    @token_required
    def get_single_post(post_id):
        return handle_get_post(post_id)
    
    @app.route('/api/posts/<int:post_id>/like', methods=['POST', 'DELETE'])
    @token_required
    def like_post(post_id):
        return handle_like_post(post_id)
    
    @app.route('/api/posts/<int:post_id>/bookmark', methods=['POST', 'DELETE'])
    @token_required
    def bookmark_post(post_id):
        return handle_bookmark_post(post_id)
    
    @app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
    @token_required
    @validate_json
    def add_comment(post_id):
        return handle_add_comment(post_id)
    
    @app.route('/api/comments/<int:comment_id>/like', methods=['POST', 'DELETE'])
    @token_required
    def like_comment(comment_id):
        return handle_like_comment(comment_id)
    
    # Analytics
    @app.route('/api/analytics/overview')
    @token_required
    @limiter.limit("60 per hour")
    def analytics():
        return handle_analytics()
    
    # =========================================================================
    # ERROR HANDLERS - COMPLETE
    # =========================================================================
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"success": False, "error": "Method not allowed"}), 405
    
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"500 error: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"success": False, "error": "Request body too large"}), 413
    
    # =========================================================================
    # MIDDLEWARE - COMPLETE
    # =========================================================================
    @app.before_request
    def log_request_info():
        if request.endpoint and request.endpoint != 'static':
            app.logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")
    
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        if os.environ.get('RAILWAY_ENVIRONMENT') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return app

# =============================================================================
# APPLICATION STARTUP
# =============================================================================
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('RAILWAY_ENVIRONMENT') != 'production'
    
    app.logger.info(f"Starting Railway-optimized Flask application on port {port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )