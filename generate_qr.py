import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def generate_qr_code(unique_id):
    # Create the URL using the unique ID
    url = f"https://assetreg.appdeft.in/?qrcode={unique_id}"
    
    # Generate the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=3,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create an image from the QR code
    qr_img = qr.make_image(fill='black', back_color='white').convert('RGB')
    
    # Use the default font or specify a path to a TTF file
    font = ImageFont.load_default()
    
    # Create a new image with space for QR code and unique ID
    total_height = qr_img.size[1] + 30
    img = Image.new('RGB', (qr_img.size[0], total_height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Paste the QR code at the top
    img.paste(qr_img, (0, 0))
    
    # Add the unique ID below the QR code
    id_text = f'ID: {unique_id}'
    id_bbox = draw.textbbox((0, 0), id_text, font=font)
    id_w, id_h = id_bbox[2] - id_bbox[0], id_bbox[3] - id_bbox[1]
    draw.text(((img.size[0] - id_w) / 2, qr_img.size[1] + 10), id_text, fill='black', font=font)
    
    # Apply rounded corners
    def add_rounded_corners(image, radius):
        mask = Image.new("L", image.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle((0, 0, image.size[0], image.size[1]), radius=radius, fill=255)
        rounded_img = Image.new("RGB", image.size)
        rounded_img.paste(image, (0, 0), mask=mask)
        return rounded_img

    img = add_rounded_corners(img, radius=15)

    # Resize the final image to 3x3 cm (118x118 pixels at 100 DPI)
    img = img.resize((118, 118), Image.LANCZOS)

    # Save the image to a file-like object
    img_io = BytesIO()
    img.save(img_io, format="PNG")
    img_io.seek(0)
    
    return img_io
