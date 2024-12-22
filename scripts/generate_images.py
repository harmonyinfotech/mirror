from PIL import Image, ImageDraw, ImageFont
import os

def create_favicon():
    # Create base image
    size = 512
    img = Image.new('RGBA', (size, size), (66, 153, 225, 0))  # Blue background
    draw = ImageDraw.Draw(img)
    
    # Draw circle
    margin = size // 8
    draw.ellipse([margin, margin, size - margin, size - margin], 
                 fill=(66, 153, 225, 255))  # Blue circle
    
    # Draw mirror text
    try:
        font = ImageFont.truetype("arial.ttf", size=size//4)
    except:
        font = ImageFont.load_default()
    
    text = "m"
    text_width = draw.textlength(text, font=font)
    text_height = size//4  # Approximate height
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    # Save different sizes
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    # Favicon sizes
    sizes = {
        'favicon-16x16.png': 16,
        'favicon-32x32.png': 32,
        'apple-touch-icon.png': 180,
        'android-chrome-192x192.png': 192,
        'android-chrome-512x512.png': 512
    }
    
    for filename, size in sizes.items():
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(static_dir, filename))

def create_og_image():
    # Create base image (1200x630 is recommended for OG images)
    width = 1200
    height = 630
    img = Image.new('RGB', (width, height), (247, 250, 252))  # Light background
    draw = ImageDraw.Draw(img)
    
    # Draw logo
    logo_size = 120
    margin = 60
    draw.ellipse([margin, margin, margin + logo_size, margin + logo_size], 
                 fill=(66, 153, 225))
    
    try:
        logo_font = ImageFont.truetype("arial.ttf", size=logo_size//2)
        title_font = ImageFont.truetype("arial.ttf", size=72)
        desc_font = ImageFont.truetype("arial.ttf", size=36)
    except:
        logo_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        desc_font = ImageFont.load_default()
    
    # Draw "m" in logo
    text = "m"
    text_width = draw.textlength(text, font=logo_font)
    x = margin + (logo_size - text_width) // 2
    y = margin + logo_size//4
    draw.text((x, y), text, font=logo_font, fill=(255, 255, 255))
    
    # Draw title
    draw.text((margin + logo_size + 40, margin), 
              "mirror.is", font=title_font, fill=(45, 55, 72))
    
    # Draw description
    desc = "Share text instantly between devices\non your network"
    draw.text((margin + logo_size + 40, margin + 100), 
              desc, font=desc_font, fill=(74, 85, 104))
    
    # Save
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    img.save(os.path.join(static_dir, 'og-image.png'))

if __name__ == "__main__":
    create_favicon()
    create_og_image()
