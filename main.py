import datetime
import os
import gmail_api_service
import image_processor_service
import salesforce_api_service
import base64
from io import BytesIO
from PIL import Image
import re

from consumer_details import CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

app.config['UPLOAD_FOLDER'] = 'uploads'
dir_actual = os.path.dirname(os.path.abspath(__file__))

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
@cross_origin()
def index():
  return "Hello World!"

@app.route('/transform_image', methods=['POST'])
@cross_origin()
def transform_image():
  data = request.get_json()

  if 'image' not in data:
    return jsonify({'error': 'No image uploaded'}), 400
  
  # Extract the base64 image string and remove the prefix if it exists
  base64_image = data['image']
  # Use a regular expression to remove the base64 prefix (data:image/...;base64,)
  base64_image = re.sub(r'^data:image\/[a-zA-Z]+;base64,', '', base64_image)
  
  # Get the image file from the request
  image_data = base64.b64decode(base64_image)
  image = Image.open(BytesIO(image_data))
  now = datetime.datetime.now()
  filename = f"{now.strftime('%Y-%m-%d %H-%M-%S')}.png"
  image_path = os.path.join(dir_actual, filename)

  # Save image to disk
  image.save(image_path)
    
  removed_background_path = image_processor_service.remove_background(image_path, filename)

  background_choice = data['background_id']

  try:
    response = image_processor_service.overlay_images(removed_background_path, background_choice)
    os.remove(os.path.join(dir_actual, filename))
    return response
  except Exception as e:
    print(f"Error processing your image: {e}")
    return jsonify({'error': 'Error processing your image'}), 500


@app.route('/send_email', methods=['POST'])
@cross_origin()
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
  
@app.route('/create_visitor_contact', methods=['POST'])
@cross_origin()
def create_visitor_contact():
  # Autheticate salesforce service
  access_token, instance_url = salesforce_api_service.generate_token(CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD)

  raw_data = request.get_json()
  
  contact_data = {
    "FirstName": raw_data.get('first_name'),
    "LastName": raw_data.get('last_name'),
    "Email": raw_data.get('email'),
    "MobilePhone": raw_data.get('mobile_phone'),
    "DoNotCall": True if (raw_data.get('opt_out_marketing') == "1") else False,
    "Do_Not_Call_Lottery__c": True if (raw_data.get('opt_out_marketing') == "1") else False,
    "HasOptedOutOfEmail": True if (raw_data.get('opt_out_marketing') == "1") else False,
    "Mail_Opt_Out__c": True if (raw_data.get('opt_out_marketing') == "1") else False,
    "SMS_Opt_Out__c": True if (raw_data.get('opt_out_marketing') == "1") else False
  }

  try:
    response = salesforce_api_service.create_contact(access_token, instance_url, contact_data)
    return jsonify(response)
  except Exception as e:
    print(f"Error creating new visitor contact: {e}")
    return jsonify({'error': 'Unexpected error while saving a new contact'}), 500


if __name__ == '__main__':
  app.run(host="localhost", port=8000, debug=True)