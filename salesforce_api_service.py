import requests
import base64

def generate_token(client_id, client_secret, username, password):
  DOMAIN = 'https://lifeflight--datacentre.sandbox.my.salesforce.com/'

  payload = {
    'grant_type': 'password',
    'client_id': client_id,
    'client_secret': client_secret,
    'username': username,
    'password': password
  }

  oauth_endpoint = 'services/oauth2/token'
  response = requests.post(DOMAIN + oauth_endpoint, data=payload)
  response.raise_for_status()  # Check if the authentication was successful
  auth_response = response.json()
    
  # Return access token and instance URL
  return auth_response['access_token'], auth_response['instance_url']

def create_contact(access_token, instance_url, contact_data_input):
  contact_url = f'{instance_url}/services/data/v57.0/sobjects/Contact'

  # Set headers with access token
  headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
  }

  contact_data = {
    "FirstName": contact_data_input.get('first_name'),
    "LastName": contact_data_input.get('last_name'),
    "Email": contact_data_input.get('email'),
    "MobilePhone": contact_data_input.get('mobile_phone'),
    "DoNotCall": True if (contact_data_input.get('opt_out_marketing') == "1") else False,
    "Do_Not_Call_Lottery__c": True if (contact_data_input.get('opt_out_marketing') == "1") else False,
    "HasOptedOutOfEmail": True if (contact_data_input.get('opt_out_marketing') == "1") else False,
    "Mail_Opt_Out__c": True if (contact_data_input.get('opt_out_marketing') == "1") else False,
    "SMS_Opt_Out__c": True if (contact_data_input.get('opt_out_marketing') == "1") else False,
    "Data_Source__c": "Data Centre"
  }

  # POST request to create a Contact object
  response = requests.post(contact_url, headers=headers, json=contact_data)

  return response.json()

def upload_image(access_token, instance_url, file_data_input):
  headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
  }
  
  content_version_url = f'{instance_url}/services/data/v56.0/sobjects/ContentVersion'
  
  # encode image file in base64
  image_path = file_data_input.get('file_path')

  with open(image_path, 'rb') as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

  user_name = (
    f"{file_data_input.get('first_name', '')}{file_data_input.get('last_name', '')}"
    if (file_data_input.get('first_name') is not None or file_data_input.get('last_name') is not None)
    else image_path
  )

  filename = f'DataCentreFilesUpload_{user_name}'
  content_version_data = {
    'Title': filename,
    'PathOnClient': f'{filename}.png',
    'VersionData': base64_image
  }

  response = requests.post(content_version_url, json=content_version_data, headers=headers)

  return response.json()

def create_content_document_link(access_token, instance_url, content_document_id, contact_id):
  content_document_link_url = f'{instance_url}/services/data/v57.0/sobjects/ContentDocumentLink'

  headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
  }

  link_data = {
    'ContentDocumentId': content_document_id,
    'LinkedEntityId': contact_id,
    'ShareType': 'V',
    'Visibility': 'AllUsers'
  }

  # POST request to create the ContentDocumentLink record
  response = requests.post(content_document_link_url, headers=headers, json=link_data)

  return response.json()

def get_content_document_id(access_token, instance_url, content_version_id):
  query_url = f"{instance_url}/services/data/v57.0/query"

  query_params = {
    'q': f"SELECT ContentDocumentId FROM ContentVersion WHERE Id = '{content_version_id}'"
  }

  headers = {'Authorization': f'Bearer {access_token}'}
  response = requests.get(query_url, headers=headers, params=query_params)

  # Parse the ContentDocumentId from the response
  records = response.json().get('records', [])
  if not records:
    raise ValueError("No ContentDocumentId found for the given ContentVersionId.")
  return records[0]['ContentDocumentId']


