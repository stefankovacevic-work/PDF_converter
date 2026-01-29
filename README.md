Markdown
# PDF and Image Converter

A specialized desktop utility designed for efficiently processing shipping labels, invoices, and product photos. This tool combines smart PDF extraction with versatile image conversion and merging capabilities, all wrapped in a modern, user-friendly interface.

## 🚀 Key Features

### 1. Smart PDF to Image Extraction
* **Intelligent Auto-Split:** Automatically detects solid black horizontal lines in shipping documents (e.g., separating a FedEx label from instructions) and extracts them as two distinct images.
* **Photo Safety Mode:** Includes a smart "Isolation Check" to ensure photos (like tire treads) are not accidentally cut, even if they contain straight lines.
* **Visual Selection Gallery:** Preview your PDF pages and select exactly which parts (Label vs. Page) you want to save.
* **High-Resolution Output:** Extracts clean, crisp images at 300 DPI.

### 2. Image to PDF Merging
* **Drag & Drop Sorting:** Visually arrange your images in the exact order you want before merging.
* **HEIC Support:** Native support for iPhone `.heic` photos—no external converters needed.
* **Multi-Format:** Seamlessly combine PNG, JPEG, BMP, TIFF, and HEIC files into a single professional PDF.

### 3. Batch Image Converter
* **Bulk Processing:** Convert hundreds of images in seconds.
* **Wide Compatibility:** Supports inputs and outputs for JPEG, PNG, TIFF, BMP, WEBP, and HEIC.

### 4. User Experience
* **Patriotic Theme:** Clean "Red, White, and Blue" interface with high-contrast elements.
* **Drag & Drop Zones:** Drag files directly from your desktop onto the specific tool card you need.
* **Background Processing:** All heavy lifting happens in the background, keeping the app responsive.
* **Silent Operation:** Console windows are suppressed for a smooth, flicker-free experience.

---

## 🛠️ Installation & Setup

### Prerequisites
* **Python 3.10+** installed on your system.
* **Poppler:** A `poppler` folder containing the `bin` directory (specifically `pdftoppm.exe`) must be present in the root directory.

### Steps 1 - 3 Are automatically done when running the build_app.bat on Windows ###
### 1. Set Up Environment
It is recommended to use a virtual environment.
python -m venv venv
venv\Scripts\activate

### 2. Install Dependencies 
Install the required Python libraries, including the specific HEIC and Drag-and-Drop modules.
pip install customtkinter pdf2image img2pdf pillow pillow-heif tkinterdnd2 packaging pyinstaller

### 3. Build the Application
Run the included build script to generate the standalone .exe.
build_app.bat
This will check for Python and Poppler.
It will install any missing dependencies.
It will compile the app into a single file: PDF_and_Image_Converter.exe.

📂 Project Structure
/
├── main.py              # Core application source code

├── build_app.bat        # Automated build script

├── make_icon.py         # Helper to generate .ico files

├── logo.png             # Source logo file

├── icon.ico             # Generated application icon

├── /poppler             # (Required) Poppler binaries folder

│   └── /bin

│       └── pdftoppm.exe

└── README.md            # This file

🧩 Technical Details
GUI Framework: CustomTkinter (Light Mode Theme)
PDF Engine: Poppler (via pdf2image)
Image Processing: Pillow (PIL) + Pillow-HEIF
Drag & Drop: TkinterDnD2
Threading: All I/O operations are threaded to prevent UI freezing.

📝 License
Internal Tool / Proprietary.
