import modal
from .configuration import PERSISTED_VOLUME_PATH

# Create the Modal app
app = modal.App("pdf-document-layout-analysis-secure")

# Create volumes for persistent storage
persisted_volume = modal.Volume.from_name("pdf-analysis-storage", create_if_missing=True)

# Build the image from your existing Dockerfile
image = (
    modal.Image.from_registry(
        "pytorch/pytorch:2.4.0-cuda11.8-cudnn9-runtime"
    )
    .env(
        {"TRANSFORMERS_VERBOSITY": "error",
         "TRANSFORMERS_NO_ADVISORY_WARNINGS": "1"}
    )
    .apt_install(
        "libgomp1", "ffmpeg", "libsm6", "libxext6", "pdftohtml", "git", "ninja-build", "g++", "qpdf", "pandoc",
        "ocrmypdf", "tesseract-ocr-fra", "tesseract-ocr-spa", "tesseract-ocr-deu", "tesseract-ocr-ara", "tesseract-ocr-mya",
        "tesseract-ocr-hin", "tesseract-ocr-tam", "tesseract-ocr-tha", "tesseract-ocr-chi-sim", "tesseract-ocr-tur",
        "tesseract-ocr-ukr"
    )
    .pip_install_from_pyproject("pyproject.toml")
    .pip_install("git+https://github.com/facebookresearch/detectron2.git@70f454304e1a38378200459dd2dbca0f0f4a5ab4")
)

@app.function(
    image=image,
    gpu="A10G",
    volumes={
        PERSISTED_VOLUME_PATH: persisted_volume
    },
    timeout=3600,
    scaledown_window=300,
    secrets=[modal.Secret.from_name("pdf-document-secret", required_keys=["API_KEY"])],  # Add API key secret
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def fastapi_app():
    """
    Serve the PDF analysis FastAPI app with API key authentication.
    """
    import os
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from .download_models import are_models_downloaded
    
    # Download models if needed - this will run on first container startup
    print("Checking if models need to be downloaded...")
    if not are_models_downloaded():
        print("Models not found, downloading...")
        download_models.remote()
        print("Models downloaded successfully")
    else:
        print("Models already available")
    
    # Import the original FastAPI app
    from .app import app as original_app
    
    # Create a new FastAPI app that wraps the original with auth
    secure_app = FastAPI(
        title="PDF Document Layout Analysis API (Secured)",
        description="Secure API for PDF document layout analysis",
        version="1.0.0"
    )
    
    # Add CORS middleware
    secure_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure as needed for your use case
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Create a middleware to add auth to all requests
    @secure_app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Skip auth for health checks (optional)
        if request.url.path in ["/health", "/openapi.json"]:
            response = await call_next(request)
            return response
        
        # Verify API key
        api_key = request.headers.get("X-API-Key")
        expected_key = os.environ.get("API_KEY")
        
        if expected_key and (not api_key or api_key != expected_key):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key"
            )
        
        response = await call_next(request)
        return response
    
    # Mount the original app (this preserves all your existing endpoints)
    secure_app.mount("/api", original_app)
    
    @secure_app.get("/health")
    async def health():
        """Public health check endpoint"""
        import torch
        return {
            "status": "healthy",
            "gpu_available": torch.cuda.is_available(),
            "models_loaded": are_models_downloaded()
        }
    
    return secure_app

@app.function(
    image=image,
    volumes={PERSISTED_VOLUME_PATH: persisted_volume},
    timeout=1800,
)
def download_models():
    """Download and cache the ML models."""    
    from .download_models import download_models
    download_models("doclaynet")
    download_models("fast")

    print("Models downloaded successfully")
    persisted_volume.commit()  # Commit the models to the volume
    return "Models downloaded and cached"

@app.local_entrypoint()
def deploy():
    """Deploy the secure service."""
    print("Pre-downloading models to volume...")
    download_models.remote()
    print("Models downloaded and cached in volume. Secure service is ready!")
    print(f"API will be available at: {fastapi_app.web_url}")
    print()
    print("🔐 SECURITY SETUP:")
    print("1. Create API key: modal secret create pdf-document-secret API_KEY=your-secret-key")
    print(f"2. Access API with: curl -X POST -F \"file=@input.pdf\" -F \"fast=true\" -H \"X-API-Key: $API_KEY\" {fastapi_app.web_url}/api/")
    print(f"3. Health check (public): curl {fastapi_app.web_url}/health")

if __name__ == "__main__":
    print("Secure PDF Analysis API Deployment")
    print("Usage:")
    print("  modal deploy modal_deployment_with_auth.py")
    print()
    print("Setup API key:")
    print("  export API_KEY=(openssl rand -hex 32)")
    print("  echo $API_KEY  # Save this key securely!")
    print("  modal secret create pdf-document-secret API_KEY=$API_KEY") 