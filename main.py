import datetime
import os
import image_processor_service
import salesforce_api_service
import base64
from io import BytesIO
from PIL import Image
import re

# from consumer_details import CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD
from flask import Flask, request, jsonify

from flask_cors import CORS, cross_origin

CONSUMER_KEY = os.environ["CONSUMER_KEY"]
CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]

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

@app.route('/create_contact_with_image', methods=['POST'])
def create_contact_with_image():
  """
  Creates a contact, uploads an image, and links the image to the contact record.
  """
  try:
    # Extract data from the request
    contact_data = request.json.get('contact_data')
    file_data = request.json.get('file_data')

    # Authenticate with Salesforce
    access_token, instance_url = salesforce_api_service.generate_token(CONSUMER_KEY, CONSUMER_SECRET, USERNAME, PASSWORD)

    # Create a new Contact
    contact_response = salesforce_api_service.create_contact(access_token, instance_url, contact_data)
    contact_id = contact_response['id']  # Extract the Contact record ID

    # Upload the image
    file_response = salesforce_api_service.upload_image(access_token, instance_url, file_data)
    content_version_id = file_response['id']  # Extract ContentVersion ID

    # Retrieve the ContentDocumentId
    content_document_id = salesforce_api_service.get_content_document_id(access_token, instance_url, content_version_id)

    # Link the file to the Contact record
    link_response = salesforce_api_service.create_content_document_link(access_token, instance_url, content_document_id, contact_id)

    return jsonify({
        'contact': contact_response,
        'file_upload': file_response,
        'content_document_link': link_response
    }), 200

  except Exception as e:
    # Handle errors
    return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
  app.run(host="localhost", port=8000, debug=True)