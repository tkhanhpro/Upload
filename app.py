from flask import Flask, request, send_from_directory, jsonify, render_template_string, redirect, url_for
from flask_httpauth import HTTPBasicAuth
import os
import uuid
import requests
import datetime
import humanize  # Để format size/date (thêm vào requirements nếu cần, nhưng dùng str cho đơn giản)

app = Flask(__name__, static_folder='static', static_url_path='')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

auth = HTTPBasicAuth()
users = {"admin": "secret"}  # Thay pass cho production

@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username

# Serve frontend
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Upload endpoint (hỗ trợ multi file)
@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'Không có file'}), 400
    urls = []
    for file in files:
        if file.filename == '':
            continue
        ext = os.path.splitext(file.filename)[1]
        filename = str(uuid.uuid4()) + ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        url = request.host_url + 'files/' + filename
        urls.append(url)
    return jsonify({'success': True, 'urls': urls})

# Convert endpoint (từ URL Catbox/ImgBB/Imgur/v.v.)
@app.route('/convert', methods=['POST'])
def convert_url():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'Không có URL'}), 400
    try:
        response = requests.get(url, stream=True)
        if response.status_code != 200:
            return jsonify({'error': 'Không tải được file từ URL'}), 400
        ext = os.path.splitext(url)[1] or '.bin'  # Default nếu không có ext
        filename = str(uuid.uuid4()) + ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        new_url = request.host_url + 'files/' + filename
        return jsonify({'success': True, 'url': new_url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve uploaded files
@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Admin panel
@app.route('/admin', methods=['GET', 'POST'])
@auth.login_required
def admin_panel():
    if request.method == 'POST':
        action = request.form.get('action')
        filename = request.form.get('filename')
        if action == 'delete' and filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
    # List files
    files = []
    total_size = 0
    search = request.args.get('search', '')
    for f in os.listdir(app.config['UPLOAD_FOLDER']):
        if search and search not in f:
            continue
        path = os.path.join(app.config['UPLOAD_FOLDER'], f)
        size = os.path.getsize(path)
        total_size += size
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
        files.append({'name': f, 'size': f"{size / 1024:.2f} KB", 'date': mtime, 'url': request.host_url + 'files/' + f})
    files.sort(key=lambda x: x['date'], reverse=True)
    return render_template_string('''
    <!doctype html>
    <html lang="vi">
    <head>
        <title>Admin Panel</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <h1 class="mb-4">Admin Panel - Quản lý File</h1>
            <p>Tổng file: {{ files|length }} | Tổng size: {{ total_size / 1024 / 1024:.2f }} MB</p>
            <form method="GET" class="mb-3">
                <input type="text" name="search" class="form-control" placeholder="Tìm file..." value="{{ search }}">
                <button type="submit" class="btn btn-primary mt-2">Tìm</button>
            </form>
            <table class="table table-striped">
                <thead><tr><th>Tên</th><th>Size</th><th>Ngày</th><th>Link</th><th>Hành động</th></tr></thead>
                <tbody>
                    {% for file in files %}
                    <tr>
                        <td>{{ file.name }}</td>
                        <td>{{ file.size }}</td>
                        <td>{{ file.date }}</td>
                        <td><a href="{{ file.url }}" target="_blank">View</a></td>
                        <td>
                            <form method="POST" style="display:inline;">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="filename" value="{{ file.name }}">
                                <button type="submit" class="btn btn-danger btn-sm">Xóa</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            <a href="/" class="btn btn-secondary">Về Trang Chủ</a>
        </div>
    </body>
    </html>
    ''', files=files, total_size=total_size, search=search)

# API Docs route
@app.route('/api-docs')
def api_docs():
    return render_template_string('''
    <!doctype html>
    <html lang="vi">
    <head>
        <title>API Docs - Simple Uploader</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style> body { padding: 20px; } pre { background: #f8f9fa; padding: 10px; border-radius: 5px; } </style>
    </head>
    <body>
        <div class="container">
            <h1>API Documentation</h1>
            <p>Base URL: <code>{{ request.host_url }}</code></p>
            
            <h2>1. Upload Files (POST /upload)</h2>
            <p>Upload multi file anonymous.</p>
            <ul>
                <li><strong>Body</strong>: Form-data với key <code>files</code> (multiple files).</li>
                <li><strong>Response</strong> (JSON): <pre>{"success": true, "urls": ["url1", "url2"]}</pre></li>
                <li><strong>cURL</strong>: <pre>curl -X POST -F "files=@file1.jpg" -F "files=@file2.png" {{ request.host_url }}upload</pre></li>
            </ul>
            
            <h2>2. Convert URL (POST /convert)</h2>
            <p>Convert (tải và lưu) từ URL (Catbox, ImgBB, Imgur, v.v.).</p>
            <ul>
                <li><strong>Body</strong>: Form-data với key <code>url</code> (string URL).</li>
                <li><strong>Response</strong> (JSON): <pre>{"success": true, "url": "new_url"}</pre></li>
                <li><strong>cURL</strong>: <pre>curl -X POST -F "url=https://example.com/image.jpg" {{ request.host_url }}convert</pre></li>
            </ul>
            
            <h2>Giới hạn</h2>
            <ul>
                <li>Max 100MB/file.</li>
                <li>Hỗ trợ mọi loại media (image, video, file).</li>
                <li>Admin API: Không public, chỉ qua /admin với auth.</li>
            </ul>
            <a href="/" class="btn btn-primary">Về Trang Chủ</a>
        </div>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
