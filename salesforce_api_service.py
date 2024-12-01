import pandas as pd
import requests

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

def create_contact(access_token, instance_url, contact_data):
  contact_url = f'{instance_url}/services/data/v57.0/sobjects/Contact'

  # Set headers with access token
  headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
  }

  # POST request to create a Contact object
  response = requests.post(contact_url, headers=headers, json=contact_data)

  return response.json()

def upload_image(access_token, instance_url, content_version_data):
  headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
  }

  content_version_url = f'{instance_url}/services/data/v56.0/sobjects/ContentDocumentLink'

  respose = requests.post(content_version_url, json=content_version_data, headers=headers)

  return respose.json()


