# Query System

A stunning, application, uploading files and querying them.

## 📁 Project Structure

```
devops-query-app/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # HTML template
├── static/
│   ├── style.css          # CSS styles
│   └── script.js          # JavaScript functionality
└── README.md              # This file
```

## 🚀 Setup Instructions

### 1. Create Project Structure

```bash
mkdir devops-query-app
cd devops-query-app
mkdir templates static
```

### 2. Copy Files

Copy the following files to their respective locations:
- `main.py` → Root directory
- `requirements.txt` → Root directory
- `index.html` → `templates/` folder
- `style.css` → `static/` folder
- `script.js` → `static/` folder

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install fastapi uvicorn python-multipart
```

### 4. Run the Application

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the Application

Open your browser and navigate to:
```
http://localhost:8000
```

## 🎯 How to Use

1. **Upload a File**: Click the upload zone or drag a file (YAML, JSON, TXT, LOG, etc.)
2. **View Details**: File information is automatically displayed
3. **Enter Query**: Type your question in the text area
4. **Get Response**: Click "Ask Question" to process and view results
