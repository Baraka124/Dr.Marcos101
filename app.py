"""
Railway-Optimized Flask Forum Application
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
# DATABASE MANAGEMENT
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
    """Initialize database schema"""
    db_manager = DatabaseManager(app)
    
    try:
        with db_manager.get_cursor() as cursor:
            # Create all tables
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
            """)

            # Create indexes for performance
            cursor.executescript("""
                CREATE INDEX IF NOT EXISTS idx_posts_user_category ON posts(user_id, category);
                CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_posts_last_activity ON posts(last_activity DESC);
                CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username COLLATE NOCASE);
            """)

            # Insert default categories
            default_categories = [
                ('General', 'General discussions and topics', '#007AFF'),
                ('Technology', 'Tech news, programming, and gadgets', '#34C759'),
                ('Science', 'Scientific discoveries and discussions', '#FF9500'),
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
# SECURITY UTILITIES
# =============================================================================
class SecurityUtils:
    @staticmethod
    def validate_username(username):
        """Validate username format and security"""
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(username) > 20:
            raise ValueError("Username must be less than 20 characters")
        if not re.match(r'^[a-zA-Z0-9_\-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return username.lower().strip()
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return password
    
    @staticmethod
    def sanitize_html(content, max_length=None):
        """Sanitize HTML content to prevent XSS"""
        if not content:
            return content
        
        allowed_tags = ['p', 'br', 'strong', 'em', 'code', 'pre']
        cleaned = bleach.clean(content, tags=allowed_tags, strip=True)
        
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned.strip()
    
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
    
    @staticmethod
    def check_password(password, hashed):
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed)
        except Exception:
            return False
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate cryptographically secure token"""
        return secrets.token_hex(length)

# =============================================================================
# AUTHENTICATION DECORATORS
# =============================================================================
def token_required(f):
    """Decorator to require JWT token for route access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        
        if not token or not token.startswith('Bearer '):
            return jsonify({"success": False, "error": "Authentication required"}), 401
        
        token = token[7:]
        
        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT id, username, is_active FROM users WHERE id = ?", (decoded["user_id"],))
                user = cursor.fetchone()
                
                if not user or not user["is_active"]:
                    return jsonify({"success": False, "error": "Invalid user"}), 401
                
                request.user_id = user["id"]
                request.username = user["username"]
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        except Exception as e:
            current_app.logger.error(f"Token validation error: {e}")
            return jsonify({"success": False, "error": "Authentication failed"}), 401
        
        return f(*args, **kwargs)
    return decorated

def validate_json(f):
    """Decorator to validate JSON request body"""
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
# UTILITY FUNCTIONS
# =============================================================================
def format_timestamp(timestamp):
    """Format timestamp for human-readable display"""
    if not timestamp:
        return "Recently"
    
    try:
        if isinstance(timestamp, str):
            post_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            post_time = timestamp
            
        now = datetime.now()
        diff = now - post_time
        
        if diff.days > 0:
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
    """Generate random avatar color for users"""
    colors = ['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE', '#5856D6']
    return random.choice(colors)

# =============================================================================
# ROUTE HANDLERS
# =============================================================================
def handle_register():
    """Handle user registration"""
    data = request.json_data
    
    try:
        username = SecurityUtils.validate_username(data.get("username", ""))
        password = SecurityUtils.validate_password(data.get("password", ""))
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                raise ValueError("Username already exists")
            
            hashed_pw = SecurityUtils.hash_password(password)
            avatar_color = generate_avatar_color()
            
            cursor.execute("INSERT INTO users (username, password, avatar_color) VALUES (?, ?, ?)",
                         (username, hashed_pw, avatar_color))
            
            user_id = cursor.lastrowid
        
        return jsonify({
            "success": True, 
            "message": "Account created successfully",
            "user_id": user_id
        })
    
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Registration error: {e}")
        return jsonify({"success": False, "error": "Registration failed"}), 500

def handle_login():
    """Handle user login"""
    data = request.json_data
    
    try:
        username = data.get("username", "").strip().lower()
        password = data.get("password", "")
        
        if not username or not password:
            raise ValueError("Username and password required")
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT id, password, username, avatar_color FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if not user or not SecurityUtils.check_password(password, user["password"]):
                raise ValueError("Invalid credentials")
            
            token = jwt.encode({
                "user_id": user["id"],
                "username": user["username"],
                "exp": datetime.utcnow() + timedelta(hours=24)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            "success": True, 
            "token": token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "avatar_color": user["avatar_color"]
            }
        })
        
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 401
    except Exception as e:
        current_app.logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": "Login failed"}), 500

def get_categories():
    """Get all categories"""
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
    """Create new post"""
    data = request.json_data
    
    try:
        category = SecurityUtils.sanitize_html(data.get("category", ""), 50)
        content = SecurityUtils.sanitize_html(data.get("content", ""), current_app.config['MAX_POST_LENGTH'])
        title = SecurityUtils.sanitize_html(data.get("title", ""), 200)
        
        if len(content.strip()) < 10:
            raise ValueError("Content must be at least 10 characters")
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("INSERT INTO posts (user_id, category, title, content) VALUES (?, ?, ?, ?)",
                         (request.user_id, category, title, content))
            
            post_id = cursor.lastrowid
        
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
    """Get posts with pagination and filtering"""
    try:
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(max(1, request.args.get('per_page', 10, type=int)), 50)
        category = request.args.get('category', '')
        
        offset = (page - 1) * per_page
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            query = "SELECT p.*, u.username, u.avatar_color FROM posts p JOIN users u ON p.user_id = u.id WHERE p.is_deleted = 0"
            params = []
            
            if category:
                query += " AND p.category = ?"
                params.append(category)
            
            query += " ORDER BY p.timestamp DESC LIMIT ? OFFSET ?"
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            
            for post in rows:
                post['formatted_timestamp'] = format_timestamp(post['timestamp'])
            
            return jsonify({
                "success": True, 
                "data": rows,
                "pagination": {
                    "page": page,
                    "per_page": per_page
                }
            })
            
    except Exception as e:
        current_app.logger.error(f"Posts retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve posts"}), 500

# =============================================================================
# FLASK APPLICATION SETUP
# =============================================================================
def create_app(config_class=RailwayConfig):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS
    CORS(app)
    
    # Security headers
    Talisman(app, content_security_policy=None, force_https=False)
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"],
        storage_uri="memory://"
    )
    
    # Logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # Initialize database
    with app.app_context():
        init_database(app)
    
    # =========================================================================
    # ROUTES
    # =========================================================================
    
    @app.route('/')
    def serve_index():
        """Serve main homepage"""
        return render_template('index.html')
    
    @app.route('/beds')
    def serve_beds():
        """Serve beds management page"""
        return render_template('beds.html')
    
    @app.route('/api/health')
    def health_check():
        """Health check endpoint"""
        return jsonify({
            "status": "healthy",
            "service": "Forum API",
            "timestamp": datetime.now().isoformat()
        })
    
    # Authentication routes
    @app.route('/api/register', methods=['POST'])
    @validate_json
    def register():
        return handle_register()
    
    @app.route('/api/login', methods=['POST'])
    @validate_json
    def login():
        return handle_login()
    
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
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        app.logger.error(f"Server error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
    return app

# =============================================================================
# APPLICATION STARTUP
# =============================================================================
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)