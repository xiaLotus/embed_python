from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, threading, time, uuid

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, 'data.json')
UPLOAD_DIR = os.path.join(BASE, 'uploads')
PREFIX = 'equip-'
lock = threading.Lock()

app = Flask(__name__, static_folder=BASE, static_url_path='')
CORS(app)

def load():
    try:
        with open(DATA_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save(d):
    tmp = DATA_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)

@app.route('/')
def index():
    return send_from_directory(BASE, 'index.html')

@app.get('/api/data')
def get_data():
    return jsonify(load())

@app.put('/api/data/<key>')
def put_data(key):
    if not key.startswith(PREFIX):
        return jsonify(error='bad key'), 400
    val = request.get_data(as_text=True)
    with lock:
        d = load()
        d[key] = val
        save(d)
    print(f'[save] {key} ({len(val)} chars) -> {DATA_FILE}')
    return jsonify(ok=True)

@app.post('/api/upload')
def upload():
    f = request.files.get('file')
    if not f:
        return jsonify(error='no file'), 400
    ext = os.path.splitext(f.filename or '')[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        ext = '.jpg'
    name = f'{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{ext}'
    f.save(os.path.join(UPLOAD_DIR, name))
    print(f'[upload] {name}')
    return jsonify(url='uploads/' + name)

@app.delete('/api/uploads/<name>')
def delete_upload(name):
    p = os.path.join(UPLOAD_DIR, os.path.basename(name))
    if os.path.isfile(p):
        os.remove(p)
        print(f'[delete] {name}')
    return jsonify(ok=True)

if __name__ == '__main__':
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        save({})
    print('data file:', DATA_FILE)
    print('uploads  :', UPLOAD_DIR)
    app.run(host='0.0.0.0', port=8000, debug=False)