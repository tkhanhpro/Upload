from flask import Flask, request, send_from_directory, jsonify
import os
import uuid

app = Flask(__name__, static_folder='static', static_url_path='')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

# Serve frontend
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# Upload endpoint (dùng cho cả web và API)
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Không có file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Chưa chọn file'}), 400
    if file:
        ext = os.path.splitext(file.filename)[1]
        filename = str(uuid.uuid4()) + ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        url = request.host_url + 'files/' + filename
        return jsonify({'success': True, 'url': url})

# Serve uploaded files
@app.route('/files/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Không chạy app.run() ở production, để Gunicorn xử lý
if __name__ == '__main__':
    app.run(debug=True)  # Chỉ dùng cho dev, comment hoặc xóa ở production
