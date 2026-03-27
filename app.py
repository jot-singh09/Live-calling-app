"""
LinguaCall - Real P2P Voice Call with Live Translation
Run:  python app.py
Open: printed URL in terminal
"""
import os, random, string, socket as _sock
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

users = {}      # sid → {user_id, lang, peer_sid}
uid_map = {}    # user_id → sid

WORDS = ['LION','WOLF','HAWK','BEAR','JADE','NOVA','BOLT','ECHO',
         'IRON','SAGE','FIRE','STORM','RIVER','PIXEL','SONIC',
         'TIGER','EAGLE','PANDA','CLOUD','COMET','FROST','AMBER',
         'BLAZE','CEDAR','DRIFT','EMBER','FLARE','GROVE','HAVEN','ROYAL']

def gen_id():
    w = random.choice(WORDS)
    n = ''.join(random.choices(string.digits, k=4))
    uid = f"{w}-{n}"
    while uid in uid_map:
        n = ''.join(random.choices(string.digits, k=4))
        uid = f"{w}-{n}"
    return uid

def get_lan_ip():
    try:
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except: return '127.0.0.1'

@app.route('/')
def index(): return render_template('index.html')

@socketio.on('connect')
def on_connect():
    sid = request.sid
    uid = gen_id()
    users[sid] = {'user_id': uid, 'lang': 'en', 'peer_sid': None}
    uid_map[uid] = sid
    emit('your_id', {'user_id': uid})

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    info = users.pop(sid, {})
    uid_map.pop(info.get('user_id'), None)
    peer = info.get('peer_sid')
    if peer and peer in users:
        users[peer]['peer_sid'] = None
        emit('call_ended', {'reason': 'disconnected'}, to=peer)

@socketio.on('set_lang')
def on_set_lang(data):
    sid = request.sid
    if sid in users: users[sid]['lang'] = data.get('lang','en')

@socketio.on('call_request')
def on_call_request(data):
    sid = request.sid
    tid = (data.get('target_id') or '').strip().upper()
    caller = users.get(sid, {})
    tsid = uid_map.get(tid)
    if not tsid: emit('call_error', {'msg': f'"{tid}" not found or offline.'}); return
    if tsid == sid: emit('call_error', {'msg': "Can't call yourself!"}); return
    if users.get(tsid, {}).get('peer_sid'): emit('call_error', {'msg': f'"{tid}" is busy.'}); return
    emit('incoming_call', {'caller_id': caller['user_id'], 'caller_sid': sid, 'caller_lang': caller.get('lang','en')}, to=tsid)
    emit('call_ringing', {'target_id': tid})

@socketio.on('call_accept')
def on_call_accept(data):
    sid = request.sid
    csid = data.get('caller_sid')
    if csid not in users: emit('call_error', {'msg': 'Caller disconnected.'}); return
    users[sid]['peer_sid'] = csid
    users[csid]['peer_sid'] = sid
    callee = users[sid]; caller = users[csid]
    emit('call_accepted', {'peer_id': callee['user_id'], 'peer_lang': callee['lang']}, to=csid)
    emit('call_started',  {'peer_id': caller['user_id'], 'peer_lang': caller['lang']})

@socketio.on('call_reject')
def on_call_reject(data):
    csid = data.get('caller_sid')
    if csid: emit('call_rejected', {}, to=csid)

@socketio.on('call_end')
def on_call_end(_=None):
    sid = request.sid
    info = users.get(sid, {})
    peer = info.get('peer_sid')
    if peer:
        emit('call_ended', {'reason': 'hung_up'}, to=peer)
        if peer in users: users[peer]['peer_sid'] = None
    info['peer_sid'] = None

@socketio.on('rtc_offer')
def on_offer(data):
    sid = request.sid
    peer = users.get(sid, {}).get('peer_sid')
    if peer: emit('rtc_offer', {'sdp': data['sdp']}, to=peer)

@socketio.on('rtc_answer')
def on_answer(data):
    sid = request.sid
    peer = users.get(sid, {}).get('peer_sid')
    if peer: emit('rtc_answer', {'sdp': data['sdp']}, to=peer)

@socketio.on('rtc_ice')
def on_ice(data):
    sid = request.sid
    peer = users.get(sid, {}).get('peer_sid')
    if peer: emit('rtc_ice', {'candidate': data['candidate']}, to=peer)

# Relay transcript to peer — peer will translate into their own language
@socketio.on('transcript')
def on_transcript(data):
    sid = request.sid
    peer = users.get(sid, {}).get('peer_sid')
    lang = users.get(sid, {}).get('lang', 'en')
    if peer:
        emit('peer_transcript', {
            'text': data.get('text',''),
            'from_lang': lang,
            'interim': data.get('interim', False)
        }, to=peer)

@socketio.on('lang_update')
def on_lang_update(data):
    sid = request.sid
    lang = data.get('lang','en')
    if sid in users: users[sid]['lang'] = lang
    peer = users.get(sid, {}).get('peer_sid')
    if peer: emit('peer_lang_changed', {'lang': lang}, to=peer)

if __name__ == '__main__':
    ip = get_lan_ip()
    print('\n' + '='*50)
    print('  🌐  LinguaCall Running!')
    print(f'  Local : http://127.0.0.1:5000')
    print(f'  WiFi  : http://{ip}:5000  ← share this')
    print('  Use Chrome for microphone support')
    print('='*50 + '\n')
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
