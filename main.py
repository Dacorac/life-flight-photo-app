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

app.config['TEMP_STORAGE'] = 'temporal'
app.config['UPLOAD_FOLDER'] = 'uploads'
dir_actual = os.path.dirname(os.path.abspath(__file__))

# Ensure the upload folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMP_STORAGE'], exist_ok=True)

@app.route('/')
@cross_origin()
def index():
  return "Hello World!"

@app.route('/transform_image', methods=['POST'])
@cross_origin()
def transform_image():
  try:
    data = request.get_json()

    if 'image' not in data:
      return jsonify({'error': 'No image uploaded'}), 400
    

    # Use a regular expression to remove the base64 prefix (data:image/...;base64,)
    base64_image = data['image']
    base64_image = re.sub(r'^data:image\/[a-zA-Z]+;base64,', '', base64_image)
    image_data = base64.b64decode(base64_image)
    image = Image.open(BytesIO(image_data))

    now = datetime.datetime.now()
    filename = f"{now.strftime('%d-%m-%Y %H:%M')}.png"
    image_path = os.path.join(app.config['TEMP_STORAGE'], filename)

    # Save original image to disk
    image.save(image_path)
      
    # Removing background and saving output image in disk
    removed_background_filename, removed_background_image = image_processor_service.remove_background(image_path, filename)
    removed_background_path = os.path.join(app.config['TEMP_STORAGE'], removed_background_filename)
    removed_background_image.save(removed_background_path)

    # Overlay background and foreground
    background_choice = data['background_id']
    overlay_images = image_processor_service.overlay_images(removed_background_path, background_choice)

    # Save final output image locally
    new_filename = f"output-{now.strftime('%d-%m-%Y %H:%M')}.png"
    final_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
    overlay_images.save(final_path)

    # encode final image in base64
    final_image = image_processor_service.encodeBase64Image(final_path)

    # Convert to string if necessary
    if isinstance(final_image, bytes):
      final_image = final_image.decode('utf-8')

    # Cleanup temporary files
    os.remove(os.path.join(app.config['TEMP_STORAGE'], removed_background_filename))
    os.remove(os.path.join(app.config['TEMP_STORAGE'], filename))

    response_data = { 'file': final_image, 'file_path': final_path }
    return jsonify(response_data), 200
  
  except Exception as e:
    print(f"Error processing the image: {e}")
    return jsonify({'error': 'Error processing the image', 'details': str(e)}), 500


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

@app.route('/create_content_version_record', methods=['POST'])
@cross_origin()
def create_content_version_record():
  # Authenticate salesforce service 
  access_token, instance_url = salesforce_api_service.generate_token(CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD)

  raw_data = request.get_json()

  # encode image file in base64
  image_path = raw_data.get('file_path')

  with open(image_path, 'rb') as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

  user_name = (
    f"{raw_data.get('first_name', '')}{raw_data.get('last_name', '')}"
    if (raw_data.get('first_name') is not None or raw_data.get('last_name') is not None)
    else image_path
  )

  filename = f'DataCenterFilesUpload_{user_name}'
  content_version_data = {
    'Title': filename,
    'PathOnClient': f'{filename}.png',
    'VersionData': base64_image
  }

  try:
    response = salesforce_api_service.upload_image(access_token, instance_url, content_version_data)
    return jsonify(response)
  except Exception as e:
    return jsonify({'error': 'Unexpected error whilesaving new record'}), 500

if __name__ == '__main__':
  app.run(host="localhost", port=8000, debug=True)