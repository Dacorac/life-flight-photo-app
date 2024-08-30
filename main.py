import datetime
import os
import gmail_api_service
import image_processor_service

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
dir_actual = os.path.dirname(os.path.abspath(__file__))

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
  return "Hello World!"

@app.route('/transform_image', methods=['POST'])
def transform_image():
  if 'image' not in request.files:
    return jsonify({'error': 'No image uploaded'}), 400
  
  # Get the image file from the request
  image_file = request.files['image']
  now = datetime.datetime.now()
  filename = f"{now.strftime('%Y-%m-%d %H-%M-%S')}-{image_file.filename}"
  image_file.save(os.path.join(dir_actual, filename))
    
  removed_background_path = image_processor_service.remove_background(os.path.join(dir_actual, filename), filename)

  background_choice = request.form['background_id']
  try:
    response = image_processor_service.overlay_images(removed_background_path, background_choice)
    os.remove(os.path.join(dir_actual, filename))
    return response
  except Exception as e:
    print(f"Error processing your image: {e}")
    return jsonify({'error': 'Error processing your image'}), 500


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