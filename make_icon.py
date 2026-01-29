from PIL import Image
import os

def create_high_quality_icon():
    try:
        if not os.path.exists("logo.png"):
            print("Error: logo.png not found.")
            return

        img = Image.open("logo.png")

        # Force High Quality settings
        # We generate a large size first, then step down
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        
        # Use High-Quality Downsampling (LANCZOS)
        img.save("icon.ico", format="ICO", sizes=sizes, quality=100, optimize=True)
        print("Success! High-quality icon.ico created.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_high_quality_icon()