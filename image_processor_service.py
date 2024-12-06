from rembg import remove
from PIL import Image
import base64

def remove_background(input_path, filename):
  output_path = f"{filename}_output.png"
  input = Image.open(input_path)
  output = remove(input)

  return output_path, output

def overlay_images(input_path, background_id):
  input = Image.open(input_path)
  print(background_id)
  # change when background images path are defined
  background_path = f"background_0{background_id}.png"
  background = Image.open(background_path)

  input = input.rotate(-20, expand=True)

  # Calculate coordinates for centered bottom alignment
  x = (background.width - input.width) // 2
  y = background.height - input.height

  # Paste the foreground image onto the background
  background.paste(input, (x, y + 100), mask=input)

  return background

def encodeBase64Image(image_path):
  # Base64 encode to return image to client
  with open(image_path, 'rb') as image_file:
    base64_bytes_image = base64.b64encode(image_file.read())
  return base64_bytes_image
