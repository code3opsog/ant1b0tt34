from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store cookie in memory (in production, use more secure storage)
roblox_cookie = None

def get_headers():
    """Get headers with Roblox cookie"""
    if not roblox_cookie:
        return None
    return {
        'Cookie': f'.ROBLOSECURITY={roblox_cookie}',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

def get_csrf_token():
    """Get CSRF token from Roblox (required for POST requests)"""
    headers = get_headers()
    if not headers:
        return None
    
    # Make a request to get CSRF token
    response = requests.post(
        'https://auth.roblox.com/v2/logout',
        headers=headers
    )
    
    return response.headers.get('x-csrf-token')

@app.route('/api/set-cookie', methods=['POST'])
def set_cookie():
    """Store the Roblox cookie"""
    global roblox_cookie
    
    data = request.json
    cookie = data.get('cookie', '').strip()
    
    if not cookie:
        return jsonify({'error': 'No cookie provided'}), 400
    
    # Validate cookie format
    if not cookie.startswith('_|WARNING:-DO-NOT-SHARE-THIS.'):
        return jsonify({'error': 'Invalid cookie format'}), 400
    
    roblox_cookie = cookie
    return jsonify({'success': True, 'message': 'Cookie saved successfully'})

@app.route('/api/test-cookie', methods=['GET'])
def test_cookie():
    """Test if the cookie is valid"""
    headers = get_headers()
    if not headers:
        return jsonify({'error': 'No cookie configured'}), 400
    
    try:
        response = requests.get(
            'https://users.roblox.com/v1/users/authenticated',
            headers=headers
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                'success': True,
                'user': {
                    'id': user_data['id'],
                    'name': user_data['name'],
                    'displayName': user_data['displayName']
                }
            })
        else:
            return jsonify({'error': 'Invalid or expired cookie'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-friend-requests', methods=['GET'])
def get_friend_requests():
    """Get all pending friend requests"""
    headers = get_headers()
    if not headers:
        return jsonify({'error': 'No cookie configured'}), 400
    
    try:
        # First get authenticated user
        user_response = requests.get(
            'https://users.roblox.com/v1/users/authenticated',
            headers=headers
        )
        
        if user_response.status_code != 200:
            return jsonify({'error': 'Authentication failed'}), 401
        
        user_id = user_response.json()['id']
        
        # Get friend requests
        requests_response = requests.get(
            f'https://friends.roblox.com/v1/users/{user_id}/friends/requests?sortOrder=Desc&limit=100',
            headers=headers
        )
        
        if requests_response.status_code == 200:
            return jsonify(requests_response.json())
        else:
            return jsonify({'error': 'Failed to fetch friend requests'}), requests_response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-user-info/<int:user_id>', methods=['GET'])
def get_user_info(user_id):
    """Get information about a specific user"""
    headers = get_headers()
    if not headers:
        return jsonify({'error': 'No cookie configured'}), 400
    
    try:
        response = requests.get(
            f'https://users.roblox.com/v1/users/{user_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch user info'}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accept-request/<int:requester_id>', methods=['POST'])
def accept_request(requester_id):
    """Accept a friend request"""
    headers = get_headers()
    if not headers:
        return jsonify({'error': 'No cookie configured'}), 400
    
    # Get CSRF token
    csrf_token = get_csrf_token()
    if csrf_token:
        headers['x-csrf-token'] = csrf_token
    
    try:
        response = requests.post(
            f'https://friends.roblox.com/v1/users/{requester_id}/accept-friend-request',
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Friend request accepted'})
        else:
            return jsonify({'error': 'Failed to accept request', 'status': response.status_code}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/decline-request/<int:requester_id>', methods=['POST'])
def decline_request(requester_id):
    """Decline a friend request"""
    headers = get_headers()
    if not headers:
        return jsonify({'error': 'No cookie configured'}), 400
    
    # Get CSRF token
    csrf_token = get_csrf_token()
    if csrf_token:
        headers['x-csrf-token'] = csrf_token
    
    try:
        response = requests.post(
            f'https://friends.roblox.com/v1/users/{requester_id}/decline-friend-request',
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Friend request declined'})
        else:
            return jsonify({'error': 'Failed to decline request', 'status': response.status_code}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-all-requests', methods=['POST'])
def process_all_requests():
    """Process all friend requests based on account age"""
    headers = get_headers()
    if not headers:
        return jsonify({'error': 'No cookie configured'}), 400
    
    data = request.json
    min_age_days = data.get('minAgeDays', 60)
    
    try:
        # Get authenticated user
        user_response = requests.get(
            'https://users.roblox.com/v1/users/authenticated',
            headers=headers
        )
        
        if user_response.status_code != 200:
            return jsonify({'error': 'Authentication failed'}), 401
        
        user_id = user_response.json()['id']
        
        # Get friend requests
        requests_response = requests.get(
            f'https://friends.roblox.com/v1/users/{user_id}/friends/requests?sortOrder=Desc&limit=100',
            headers=headers
        )
        
        if requests_response.status_code != 200:
            return jsonify({'error': 'Failed to fetch friend requests'}), requests_response.status_code
        
        friend_requests = requests_response.json().get('data', [])
        
        if not friend_requests:
            return jsonify({
                'success': True,
                'processed': 0,
                'accepted': 0,
                'declined': 0,
                'results': []
            })
        
        # Get CSRF token for POST requests
        csrf_token = get_csrf_token()
        if csrf_token:
            headers['x-csrf-token'] = csrf_token
        
        results = []
        accepted_count = 0
        declined_count = 0
        
        for friend_request in friend_requests:
            requester_id = friend_request['id']
            requester_name = friend_request.get('name', 'Unknown')
            
            # Get user info to check account age
            user_info_response = requests.get(
                f'https://users.roblox.com/v1/users/{requester_id}',
                headers=headers
            )
            
            if user_info_response.status_code != 200:
                results.append({
                    'userId': requester_id,
                    'username': requester_name,
                    'action': 'error',
                    'reason': 'Failed to fetch user info'
                })
                continue
            
            user_info = user_info_response.json()
            account_created = datetime.fromisoformat(user_info['created'].replace('Z', '+00:00'))
            account_age_days = (datetime.now(account_created.tzinfo) - account_created).days
            
            # Decide action based on account age
            if account_age_days >= min_age_days:
                # Accept
                accept_response = requests.post(
                    f'https://friends.roblox.com/v1/users/{requester_id}/accept-friend-request',
                    headers=headers
                )
                
                if accept_response.status_code == 200:
                    accepted_count += 1
                    results.append({
                        'userId': requester_id,
                        'username': requester_name,
                        'action': 'accepted',
                        'accountAge': account_age_days
                    })
                else:
                    results.append({
                        'userId': requester_id,
                        'username': requester_name,
                        'action': 'error',
                        'reason': 'Failed to accept'
                    })
            else:
                # Decline
                decline_response = requests.post(
                    f'https://friends.roblox.com/v1/users/{requester_id}/decline-friend-request',
                    headers=headers
                )
                
                if decline_response.status_code == 200:
                    declined_count += 1
                    results.append({
                        'userId': requester_id,
                        'username': requester_name,
                        'action': 'declined',
                        'accountAge': account_age_days,
                        'reason': f'Account too young ({account_age_days} days < {min_age_days} days)'
                    })
                else:
                    results.append({
                        'userId': requester_id,
                        'username': requester_name,
                        'action': 'error',
                        'reason': 'Failed to decline'
                    })
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return jsonify({
            'success': True,
            'processed': len(friend_requests),
            'accepted': accepted_count,
            'declined': declined_count,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cookieConfigured': roblox_cookie is not None
    })

if __name__ == '__main__':
    print("=" * 60)
    print("Roblox Friend Filter Backend Server")
    print("=" * 60)
    print("Server starting on http://localhost:5000")
    print("\nAvailable endpoints:")
    print("  POST /api/set-cookie          - Set Roblox cookie")
    print("  GET  /api/test-cookie         - Test cookie validity")
    print("  GET  /api/get-friend-requests - Get pending requests")
    print("  GET  /api/get-user-info/<id>  - Get user information")
    print("  POST /api/accept-request/<id> - Accept friend request")
    print("  POST /api/decline-request/<id>- Decline friend request")
    print("  POST /api/process-all-requests- Process all requests")
    print("  GET  /api/health              - Health check")
    print("=" * 60)
    print("\n⚠️  Make sure to install dependencies:")
    print("   pip install flask flask-cors requests")
    print("\n")
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
