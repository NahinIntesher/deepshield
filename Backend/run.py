import uvicorn
import sys

if __name__ == "__main__":
    print("Python:", sys.executable)
    print("Starting Deepfake Literacy & Human-AI Evaluation Backend API")
    print("Host: http://127.0.0.1:8000")
    print("Interactive API Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False, workers=1)
