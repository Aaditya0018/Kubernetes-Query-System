import os
import shutil
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_agent_langchain import KubernetesSREAgent


sre_agent = KubernetesSREAgent()



app = FastAPI(title="DevOps Cloud Query System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- MODIFIED CONSTANTS ---
UPLOAD_DIR = "uploads"
CONFIG_FILENAME = "config" # The constant name for the uploaded file
os.makedirs(UPLOAD_DIR, exist_ok=True)
CONFIG_FILE_PATH = os.path.join(UPLOAD_DIR, CONFIG_FILENAME)
# --- END MODIFIED CONSTANTS ---

# Store session data in memory (kept for /query and /clear, though simplified)
session_data = {}

class QueryRequest(BaseModel):
    query: str
    session_id: str

class ClearRequest(BaseModel):
    session_id: str


@app.on_event("shutdown")
def cleanup_on_shutdown():
    """
    Deletes the 'config' file when the FastAPI application process is stopped.
    """
    print("\n--- Running Shutdown Cleanup ---")
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            os.remove(CONFIG_FILE_PATH)
            print(f"Successfully deleted config file at: {CONFIG_FILE_PATH}")
        except Exception as e:
            print(f"Error deleting config file on shutdown: {e}")
    else:
        print("Config file not found. Nothing to delete.")
    
    # You could also call sre_agent.start_new_session() here if needed, 
    # but the primary goal is resource cleanup.
    
    print("--- Shutdown Cleanup Complete ---")


# --- MODIFIED FILE UPLOAD ENDPOINT ---
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), session_id: str = Form(...)):
    """
    Restricts to one file, saves it as 'config' in the 'uploads' folder, 
    overwriting any previous file.
    """
    try:
        # The file will be stored directly in the UPLOAD_DIR with the constant name
        file_path = os.path.join(UPLOAD_DIR, CONFIG_FILENAME)
        
        # Overwrite the existing 'config' file if it exists
        
        # Save file to disk with constant name 'config'
        with open(file_path, "wb") as buffer:
            # Important: Ensure the file pointer is at the beginning before copying
            await file.seek(0) 
            shutil.copyfileobj(file.file, buffer)
            
        # Optional: Store simple confirmation data in session_data (if still needed)
        if session_id not in session_data:
            session_data[session_id] = {}
            
        # Clear previous file info for this session and store the new one
        session_data[session_id] = {
            "filename": file.filename, # Store original filename for reference
            "filepath": file_path,     # The constant path
            "content_type": file.content_type,
            "size": os.path.getsize(file_path)
        }

        return JSONResponse({
            "message": f"File uploaded and saved as '{CONFIG_FILENAME}' successfully.",
            "saved_as": CONFIG_FILENAME,
            "original_filename": file.filename,
            "filepath": file_path
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error uploading file: {str(e)}"})
# --- END MODIFIED FILE UPLOAD ENDPOINT ---

# --- MODIFIED QUERY ENDPOINT (Simplified Check) ---
@app.post("/query")
async def process_query(request: QueryRequest):
    try:
        session_id = request.session_id
        query = request.query
        
        # Check if the constant 'config' file exists
        config_file_path = os.path.join(UPLOAD_DIR, CONFIG_FILENAME)
        if not os.path.exists(config_file_path):
            return JSONResponse(status_code=400, content={"detail": "Required file 'config' not found in uploads folder."})
        
        # Now, you can pass the file path to your agent (or access it from the agent's logic)
        # Example of agent using the file (assuming the agent's chat method handles loading it)
        # Note: In a real scenario, you might want to pass the path explicitly or ensure the agent logic knows to look there.
        # For this example, let's assume the agent uses the file via logic similar to agent_logic.py
        
        response = sre_agent.chat(query)
        
        # Get the original filename for the response message if available
        original_filename = session_data.get(session_id, {}).get("filename", CONFIG_FILENAME)
        
        return JSONResponse({
            "response": response,
            "query": query,
            "file_analyzed": f"{CONFIG_FILENAME} (Original: {original_filename})"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error processing query: {str(e)}"})
# --- END MODIFIED QUERY ENDPOINT ---

# --- CLEANUP ENDPOINT (Simplified) ---
@app.post("/clear")
async def clear_history(request: ClearRequest):
    """Manual clear button - clears current session and deletes the 'config' file."""
    try:
        sre_agent.start_new_session()
        
        session_id = request.session_id
        
        # Delete the constant file
        config_file_path = os.path.join(UPLOAD_DIR, CONFIG_FILENAME)
        if os.path.exists(config_file_path):
            os.remove(config_file_path)
        
        # Clear session data from memory
        if session_id in session_data:
            del session_data[session_id]

        return {"message": f"Upload history cleared successfully. '{CONFIG_FILENAME}' deleted."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error clearing history: {str(e)}"})

# --- CLEANUP ALL (Simplified) ---
@app.post("/cleanup-all")
async def cleanup_all_sessions():
    """Deletes the constant 'config' file and clears all memory."""
    try:
        sre_agent.start_new_session()
        
        config_file_path = os.path.join(UPLOAD_DIR, CONFIG_FILENAME)
        deleted_count = 0
        
        if os.path.exists(config_file_path):
            os.remove(config_file_path)
            deleted_count = 1
        
        # Clear all session data from memory
        session_data.clear()
        
        return {
            "message": f"All sessions cleaned up successfully. Removed {deleted_count} file(s).",
            "deleted_count": deleted_count
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error cleaning up all sessions: {str(e)}"})
# --- END CLEANUP ALL (Simplified) ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "DevOps Cloud Query System"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)