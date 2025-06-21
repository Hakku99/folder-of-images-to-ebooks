# Image Folder to EPUB Converter

A user-friendly desktop application to convert folders of images (like comics or manga chapters) into beautiful, seamless EPUB files, perfectly formatted for e-readers like Kobo and Kindle.

This tool was designed to be fast and intuitive, solving common problems like extra blank pages and confusing chapter breaks.

![App Screenshot](https://i.imgur.com/uG9Z4vX.png)

---

## ✨ Features

-   **User-Friendly Interface:** A clean, modern, and intuitive UI.
-   **Drag & Drop:** Easily add multiple folders by dragging them directly into the application.
-   **Batch Processing:** Convert hundreds of folders in a single click.
-   **Optimized for E-readers:** Automatically formats the EPUB to prevent extra blank pages between images.
-   **No Index Page:** Generated EPUBs flow directly from one image to the next without an intrusive table of contents.
-   **Real-time Logging:** See the status of your conversions as they happen.
-   **Standalone Executable:** Can be easily compiled into a single `.exe` file for distribution.

---

## 🚀 Installation & Usage (From Source)

These instructions explain how to run the application directly from the source code.

### Prerequisites

-   Python 3.8 or newer
-   `pip` for installing packages

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/Hakku99/folder-of-images-to-epub.git
cd folder-of-images-to-epub
```

### 2. Create `requirements.txt`

Create a file named `requirements.txt` in the project's root directory and add the following lines. This file lists all the necessary libraries.

```
Pillow
ebooklib
tkinterdnd2
```

### 3. Install Dependencies

Open your terminal or command prompt in the project directory and run the following command to install the required libraries:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

Once the dependencies are installed, you can run the application with this command:

```bash
python image-to-epub.py
```
*(This assumes your main Python script is named `image-to-epub.py`)*

The application's graphical user interface should now appear.

---

## 📦 How to Compile into an EXE File

You can bundle this application into a single standalone executable (`.exe`) for Windows, so it can be run without needing Python installed.

### 1. Install PyInstaller

If you don't already have it, install `PyInstaller`, a tool for converting Python scripts into executables:

```bash
pip install pyinstaller
```

### 2. Run the Build Command

From your terminal, in the project's root directory, run the following command:

```bash
pyinstaller --onefile --windowed --name="Image to EPUB Converter" --icon=icon.ico image-to-epub.py
```
**Command Breakdown:**
-   `--onefile`: Bundles everything into a single executable file.
-   `--windowed`: Prevents the command-line console from appearing when the app runs.
-   `--name="Image to EPUB Converter"`: Sets the final name of your `.exe` file.
-   `--icon=icon.ico`: (Optional) If you have an icon file named `icon.ico` in the same directory, this will set it as the application's icon.

### 3. Find Your Executable

After the process completes, look for a new folder named `dist`. Your finished `Image to EPUB Converter.exe` will be inside this folder.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
