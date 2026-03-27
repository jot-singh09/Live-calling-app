from app import app, socketio
import ssl
import os

if __name__ == '__main__':
    # Generate self-signed cert if it doesn't exist
    if not os.path.exists('cert.pem') or not os.path.exists('key.pem'):
        print("⚠️  Generating self-signed certificate...")
        os.system('openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=localhost"')
    
    print('\n' + '='*50)
    print('  🌐  LinguaCall Running with HTTPS!')
    print('  Local : https://127.0.0.1:5000')
    print('  ⚠️  Accept security warning (self-signed cert)')
    print('  Use Chrome for microphone support')
    print('='*50 + '\n')
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, 
                 ssl_context=('cert.pem', 'key.pem'))