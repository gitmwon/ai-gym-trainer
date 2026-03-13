import jwt
import os
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv('JWT_SECRET')

def verify_token(token):
    """Verify JWT token and return user_id"""
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        # Node.js backend uses 'id' field in JWT
        user_id = decoded.get('id') or decoded.get('_id') or decoded.get('userId')
        if not user_id:
            return {'valid': False, 'error': 'No user ID in token'}
        return {'valid': True, 'userId': str(user_id)}
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}
