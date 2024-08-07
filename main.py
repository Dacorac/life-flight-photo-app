import os
import gmail_api_service

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
  return "Hello World!"

@app.route('/send_email', methods=['POST'])
def send_email():
  if 'file' not in request.files:
    return jsonify({"error": "No file part in the request"}), 400
  
  file = request.files['file']

  if file.filename == '':
    return jsonify({"error": "No selected file"}), 400
  
  filename = secure_filename(file.filename)
  file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
  file.save(file_path)

  sender = request.form.get('sender', '')
  subject = request.form.get('subject', 'No Subject')
  body = request.form.get('body', '')
  to_email = request.form.get('to_email')

  if not to_email:
    return jsonify({"error": "Recipient email is required"}), 400

  message = gmail_api_service.create_message_with_attachment(sender, to_email, subject, body, file_path)

  try:
    response = gmail_api_service.send_message('me', message)
    os.remove(file_path)
    return jsonify(response)
  except Exception as e:
    print(f"Error sending email: {e}")
    return jsonify({'error': 'Unexpected error while sending email'}), 500

if __name__ == '__main__':
  app.run(host="localhost", port=8000, debug=True)