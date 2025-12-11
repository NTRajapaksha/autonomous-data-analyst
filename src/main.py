import sys
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.data_agent import data_agent_app
from src.sandbox import PythonSandbox
from langchain_core.messages import HumanMessage

# Initialize App
app = FastAPI()

# Create directories if they don't exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount 'static' so the HTML can access CSS/JS and generated plots
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Global State (Simple Memory for Demo) ---
# In a real production app, use Redis or a Database
session_state = {
    "sandbox": PythonSandbox(),
    "chat_history": [],
    "csv_path": None
}

class ChatRequest(BaseModel):
    message: str

@app.get("/")
async def read_root():
    return JSONResponse(content={"message": "Go to /static/index.html to see the UI"})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Handle CSV Upload"""
    file_path = f"uploads/{file.filename}"
    
    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Load into Sandbox
    msg = session_state["sandbox"].load_data(file_path)
    session_state["csv_path"] = file_path
    
    return {"status": "success", "message": msg, "filename": file.filename}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Run the Agent"""
    if not session_state["csv_path"]:
        raise HTTPException(status_code=400, detail="Please upload a CSV first.")

    user_msg = request.message
    
    # Run Agent
    inputs = {
        "messages": [HumanMessage(content=user_msg)],
        "csv_path": session_state["csv_path"],
        "sandbox": session_state["sandbox"],
        "retry_count": 0
    }
    
    try:
        final_state = data_agent_app.invoke(inputs)
        bot_response = final_state["messages"][-1].content
        
        # Check for generated image
        image_url = None
        if os.path.exists("output_plot.png"):
            # Move plot to static folder so frontend can see it
            new_name = f"plot_{len(session_state['chat_history'])}.png"
            static_path = os.path.join("static", new_name)
            shutil.move("output_plot.png", static_path)
            image_url = f"/static/{new_name}"

        # Update History
        session_state["chat_history"].append({"role": "user", "content": user_msg})
        session_state["chat_history"].append({"role": "assistant", "content": bot_response})

        return {
            "response": bot_response,
            "image": image_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))