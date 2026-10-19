# A3-CIM_MRO 設備維運狀態網頁 — Flask 後台修改說明

## 目標
原本所有資料存在瀏覽器 localStorage，換電腦或清除瀏覽器資料就會消失。
改成由 Flask 後台集中儲存：文字資料存 `data.json`，圖片存 `uploads/` 資料夾。
前端程式碼改動最少（index.html 只改 4 個地方），`support.js` 完全不動。

## 最終資料夾結構
```
A3-CIM_MRO/
├── app.py              ← 新增：Flask 後台
├── start.bat           ← 新增：一鍵啟動
├── data.json           ← 自動產生：文字資料
├── uploads/            ← 自動產生：圖片檔
├── index.html          ← 修改 4 處
├── support.js          ← 不動
└── assets/mascot.png   ← 不動
```

## 啟動方式
1. 第一次先安裝套件：`pip install flask flask-cors`
2. 雙擊 `start.bat`，會自動開啟 `http://localhost:8000`
3. 終端機視窗保持開著，每次存檔會印 `[save] ...`、上傳圖片印 `[upload] ...`

> 也可以直接雙擊 index.html 開（file://），shim 會自動改打 `http://127.0.0.1:8000`，
> 但 `app.py` 仍然必須先執行著。

---

## index.html 修改內容（共 4 處）

### ① `<head>` 區塊 — 換掉 support.js 載入方式

**找到：**
```html
<script src="./support.js"></script>
```

**換成：**
```html
<style>x-dc{display:none}</style>
<script>
(function(){
  var P='equip-';
  window.__API_BASE=(location.protocol==='file:' ? 'http://127.0.0.1:8000/' : '');
  var API=window.__API_BASE+'api/data';
  var put=function(k,v){
    fetch(API+'/'+encodeURIComponent(k),{method:'PUT',headers:{'Content-Type':'text/plain;charset=utf-8'},body:v})
      .then(function(r){ if(!r.ok) console.error('[save fail]',k,r.status); })
      .catch(function(e){ console.error('[save fail]',k,e); });
  };
  fetch(API).then(function(r){return r.json();}).then(function(d){
    var ks=Object.keys(d);
    if(ks.length){ ks.forEach(function(k){ try{localStorage.setItem(k,d[k]);}catch(e){} }); }
    else { for(var i=0;i<localStorage.length;i++){ var k=localStorage.key(i); if(k.indexOf(P)===0) put(k,localStorage.getItem(k)); } }
  }).catch(function(e){ console.error('[load fail] 後端未啟動？請先執行 app.py',e); }).then(function(){
    var orig=Storage.prototype.setItem, timers={};
    Storage.prototype.setItem=function(k,v){
      orig.call(this,k,v);
      if(this===localStorage && k.indexOf(P)===0){ clearTimeout(timers[k]); timers[k]=setTimeout(function(){ put(k,v); },400); }
    };
    var s=document.createElement('script'); s.src='./support.js'; document.head.appendChild(s);
  });
})();
</script>
```

**原理：**
- 頁面開啟時先 GET `/api/data` 把 `data.json` 內容塞回 localStorage，再載入 `support.js`
- 攔截 `localStorage.setItem`，所有 `equip-` 開頭的 key 寫入時，延遲 400ms 後 PUT 到後台
- 第一次啟動（`data.json` 是空的）會把瀏覽器現有的 localStorage 資料自動上傳，舊資料不會遺失
- `window.__API_BASE` 給 ② ③ ④ 的圖片功能共用

---

### ② `class Component` 內 — 新增圖片上傳 helper

**找到：**
```js
  static dmgOpts(cur) {
```

**在它的上方插入：**
```js
  static imgSrc(s) { return /^(data:|https?:)/.test(s) ? s : (window.__API_BASE || '') + s; }
  static async upload(file) {
    const data = await Component.shrink(file); if (!data) return null;
    try {
      const blob = await (await fetch(data)).blob();
      const fd = new FormData(); fd.append('file', blob, (file.name || 'img').replace(/\.[^.]+$/, '') + '.jpg');
      const r = await fetch((window.__API_BASE || '') + 'api/upload', { method: 'POST', body: fd });
      const j = await r.json(); if (j && j.url) return j.url;
    } catch (e) { console.error('[upload fail]', e); }
    return data;
  }
```

**原理：**
- `upload()`：圖片先在瀏覽器縮到 1280px、轉 JPG，再 POST 到 `/api/upload`，回傳 `uploads/xxx.jpg` 這種短路徑存進 JSON
- `imgSrc()`：顯示時把短路徑補成完整網址（localhost 或 file:// 開都能顯示）
- 後端沒開時自動退回舊的 base64 模式

---

### ③ `renderVals()` 內 — 替換 imgList / imgAdd

**找到：** `const imgList = ` 開始，到 `const imgAdd = ...` 結尾的 `};` 為止（原本約 10 行）

**整段換成：**
```js
    const imgList = (x, f) => (x[f] || []).map((src, k) => ({ src, bg: `url("${Component.imgSrc(src)}")`, w: 220, view: () => this.setState({ viewImg: Component.imgSrc(src) }),
      del: () => { if (confirm('移除這張圖片？')) {
        saveImps((this.state[SK] || []).map(y => y.id === x.id ? { ...y, [f]: (y[f] || []).filter((_, j) => j !== k) } : y));
        if (/^uploads\//.test(src)) fetch((window.__API_BASE || '') + 'api/' + src, { method: 'DELETE' }).catch(() => {});
      } } }));
    const imgAdd = (x, f) => async e => {
      const files = [...(e.target.files || [])]; e.target.value = '';
      const out = [];
      for (const file of files) out.push(await Component.upload(file));
      const next = (this.state[SK] || []).map(y => y.id === x.id ? { ...y, [f]: [...(y[f] || []), ...out.filter(Boolean)] } : y);
      try { localStorage.setItem(LK, JSON.stringify(next)); this.setState({ [SK]: next }); }
      catch (err) { alert('圖片儲存失敗：後端未啟動，請先執行 app.py'); }
    };
```

**原理：**
- 上傳改呼叫 `Component.upload()`，不再把 base64 塞 localStorage（解決 5MB 爆掉的問題）
- 按 × 移除圖片時，同步 DELETE 伺服器上的檔案

---

### ④ `exportPptx()` 內 — PowerPoint 匯出圖片

**找到：**
```js
si.addImage({ data: src, x: 0.4 + k * 6.37,
```

**換成：**
```js
si.addImage({ ...(/^data:/.test(src) ? { data: src } : { path: Component.imgSrc(src) }), x: 0.4 + k * 6.37,
```
（該行其餘部分不動）

**原理：** 新上傳的圖是網址，pptxgenjs 要用 `path`；舊的 base64 圖仍用 `data`，兩種都相容。

---

## app.py（完整）

```python
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
```

## start.bat
```bat
@echo off
cd /d "%~dp0"
pip install flask flask-cors -q
start "" http://localhost:8000
python app.py
pause
```

---

## API 一覽
| 方法 | 路徑 | 用途 |
|---|---|---|
| GET | `/api/data` | 讀取全部資料（`data.json`） |
| PUT | `/api/data/<key>` | 寫入單一 key（body 為字串） |
| POST | `/api/upload` | 上傳圖片，回傳 `{"url":"uploads/xxx.jpg"}` |
| DELETE | `/api/uploads/<檔名>` | 刪除圖片檔 |

`data.json` 格式：
```json
{ "equip-status-lights": "...", "equip-status-improve": "...", "equip-car-data": "..." }
```
每個 key 的值就是原本存進 localStorage 的字串，前端讀寫邏輯完全不用動。

## 常見問題
- **Console 出現 `Access to fetch at 'file:///...index.html'`**：這是 `support.js` 自己重抓頁面的行為，在 file:// 下會被擋，無害可忽略；用 localhost 開就不會出現。
- **改了東西但 `data.json` 沒變**：確認 `app.py` 終端機是否有印 `[save]`；沒有的話 F12 → Network 看 PUT 請求是否失敗。
- **多人同時編輯**：目前是「最後寫入的為準」，沒有衝突處理。
- **備份**：整個資料夾複製即可（`data.json` + `uploads/`）。