from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from middleware.auth import verify_token
from workout_analyzer import WorkoutAnalyzer
import cv2 as cv
import mediapipe as mp
import numpy as np
import base64
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["http://localhost:5174"])
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active workout sessions
active_sessions = {}

@socketio.on('connect')
def handle_connect():
    print('✅ Client connected')
    emit('connection_status', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('❌ Client disconnected')

@socketio.on('start_workout')
def handle_start_workout(data):
    """Initialize a new workout session"""
    token = data.get('token')
    workout_type = data.get('workout')
    
    # Verify token
    if not token:
        emit('error', {'message': 'Authentication required'})
        return
    
    auth_result = verify_token(token)
    if not auth_result['valid']:
        emit('error', {'message': auth_result['error']})
        return
    
    user_id = auth_result['userId']
    
    # Create new analyzer for this session
    try:
        analyzer = WorkoutAnalyzer(workout_type)
        active_sessions[user_id] = analyzer
        
        emit('workout_started', {
            'message': f'Started {workout_type} workout',
            'userId': user_id
        })
        print(f'✅ Started workout session for user {user_id}: {workout_type}')
    except Exception as e:
        emit('error', {'message': f'Failed to start workout: {str(e)}'})

@socketio.on('video_frame')
def handle_frame(data):
    """Process a video frame"""
    token = data.get('token')
    frame_data = data.get('frame')
    
    # Verify token
    if not token:
        emit('error', {'message': 'Authentication required'})
        return
    
    auth_result = verify_token(token)
    if not auth_result['valid']:
        emit('error', {'message': auth_result['error']})
        return
    
    user_id = auth_result['userId']
    
    # Check if user has active session
    if user_id not in active_sessions:
        emit('error', {'message': 'No active workout session. Please start workout first.'})
        return
    
    try:
        # Decode base64 frame
        frame = decode_base64_frame(frame_data)
        
        # Analyze frame
        analyzer = active_sessions[user_id]
        result = analyzer.analyze_frame(frame)
        
        # Extract pose landmarks if detected
        landmarks = []
        if hasattr(analyzer.detector, 'results') and analyzer.detector.results and analyzer.detector.results.pose_landmarks:
            for landmark in analyzer.detector.results.pose_landmarks.landmark:
                landmarks.append({
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                })
            print(f'✅ Pose detected - reps={result.get("reps")}, landmarks={len(landmarks)}')
        else:
            print('⚠️ No pose detected')
        
        # Add landmarks to result
        result['landmarks'] = landmarks
        
        # Send feedback (without frame image)
        emit('workout_feedback', result)
        
    except Exception as e:
        emit('error', {'message': f'Frame processing error: {str(e)}'})
        print(f'❌ Error processing frame: {str(e)}')
        import traceback
        traceback.print_exc()

@socketio.on('stop_workout')
def handle_stop_workout(data):
    """Stop workout session"""
    token = data.get('token')
    
    if not token:
        emit('error', {'message': 'Authentication required'})
        return
    
    auth_result = verify_token(token)
    if not auth_result['valid']:
        emit('error', {'message': auth_result['error']})
        return
    
    user_id = auth_result['userId']
    
    if user_id in active_sessions:
        final_reps = active_sessions[user_id].reps
        del active_sessions[user_id]
        
        emit('workout_stopped', {
            'message': 'Workout session ended',
            'finalReps': int(final_reps)
        })
        print(f'✅ Stopped workout session for user {user_id}')
    else:
        emit('error', {'message': 'No active workout session'})

def decode_base64_frame(frame_data):
    """Decode base64 image to OpenCV format"""
    try:
        # Remove data URL prefix if present
        if 'base64,' in frame_data:
            frame_data = frame_data.split('base64,')[1]
        
        # Decode base64
        img_bytes = base64.b64decode(frame_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # Decode image
        frame = cv.imdecode(nparr, cv.IMREAD_COLOR)
        
        return frame
    except Exception as e:
        raise Exception(f'Failed to decode frame: {str(e)}')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'service': 'AI Workout Analyzer'}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    print(f'🚀 Starting AI Workout Server on port {port}...')
    print(f'📡 WebSocket endpoint: ws://localhost:{port}')
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
