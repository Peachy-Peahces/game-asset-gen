"""
game-asset-gen - AI 2D Game Asset Generator
FastAPI backend for generating 2D game assets via SiliconFlow API (Tongyi-MAI/Z-Image-Turbo)
"""
import io
import json
import os
import ssl
import time
import uuid
from pathlib import Path
from typing import Optional
import urllib.request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

# Configuration
SF_API_URL = "https://api.siliconflow.cn/v1/images/generations"
SF_API_KEY = os.environ.get("SF_API_KEY", "sk-qldnafwtngpczmpvxbiwezsdwvpqhenneptfdbnqutwghkxx")
SF_MODEL = "Tongyi-MAI/Z-Image-Turbo"
SSL_CTX = ssl.create_default_context()
GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(exist_ok=True)

# Prompt Templates
PROMPT_TEMPLATES = {
    "character": "pixel art game sprite of {prompt}, standing pose, front view, transparent background, 16-bit RPG style, game asset",
    "scene": "pixel art game background, {prompt}, top-down view, 16-bit RPG style, game environment asset",
    "item": "pixel art game item icon, {prompt}, centered, transparent background, 16-bit RPG style, game asset",
    "ui": "pixel art game UI element, {prompt}, clean design, 16-bit RPG style, transparent background",
    "tileset": "pixel art game tileset, {prompt}, seamless tileable, top-down view, 16-bit RPG style",
}

STYLE_SUFFIX = {
    "pixel": "pixel art style, 8-bit to 16-bit",
    "cartoon": "cartoon style, vibrant colors",
    "jp_rpg": "Japanese RPG style, SNES aesthetic",
}

SIZE_MAP = {
    "16x16": (16, 16), "32x32": (32, 32), "64x64": (64, 64),
    "128x128": (128, 128), "256x256": (256, 256), "512x512": (512, 512),
}

app = FastAPI(title="Game Asset Gen")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")

class GenerateRequest(BaseModel):
    prompt: str
    asset_type: str = "character"
    style: str = "pixel"
    size: str = "128x128"

def build_prompt(req):
    template = PROMPT_TEMPLATES.get(req.asset_type, PROMPT_TEMPLATES["character"])
    base = template.format(prompt=req.prompt)
    style = STYLE_SUFFIX.get(req.style, "")
    return f"{base}, {style}".strip(",")

def generate_fallback(prompt, size="128x128"):
    w, h = SIZE_MAP.get(size, (128, 128))
    colors = [(60, 120, 200), (200, 80, 80), (80, 180, 80), (180, 140, 50)]
    color = colors[abs(hash(prompt)) % len(colors)]
    img = Image.new("RGBA", (w, h), (*color, 255))
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            if (x // 8 + y // 8) % 2 == 0:
                img.putpixel((x, y), (*color[:3], 180))
    filename = f"fallback_{uuid.uuid4().hex[:8]}.png"
    filepath = GENERATED_DIR / filename
    img.save(filepath, "PNG")
    return filepath

def remove_bg_simple(img):
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    data = img.getdata()
    new_data = [(255, 255, 255, 0) if (r > 230 and g > 230 and b > 230) else (r, g, b, a) for r, g, b, a in data]
    img.putdata(new_data)
    return img

def call_sf_api(prompt, max_retries=2):
    """Call SiliconFlow image generation API using urllib (compatible with Python 3.8)."""
    headers = {
        "Authorization": f"Bearer {SF_API_KEY}",
        "Content-Type": "application/json",
    }
    data = json.dumps({
        "model": SF_MODEL,
        "prompt": prompt,
        "image_size": "512x512",
    }).encode("utf-8")
    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(SF_API_URL, data=data, method="POST")
            for k, v in headers.items():
                req.add_header(k, v)
            r = urllib.request.urlopen(req, timeout=30, context=SSL_CTX)
            resp = json.loads(r.read().decode())
            img_url = resp["images"][0]["url"]
            # Download the actual image bytes
            img_req = urllib.request.Request(img_url)
            img_data = urllib.request.urlopen(img_req, timeout=15, context=SSL_CTX).read()
            return img_data
        except Exception as e:
            print(f"SF Error (attempt {attempt+1}): {e}")
            if attempt < max_retries:
                time.sleep(5)
    return None

def resize_image(img, size_str):
    target = SIZE_MAP.get(size_str)
    if target:
        img = img.convert("RGBA").resize(target, Image.NEAREST if max(target) <= 128 else Image.LANCZOS)
    return img

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/generate")
async def generate_asset(req: GenerateRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "prompt required")
    full_prompt = build_prompt(req)
    image_bytes = call_sf_api(full_prompt)
    filepath = None
    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = resize_image(img, req.size)
            img = remove_bg_simple(img)
            filename = f"asset_{uuid.uuid4().hex[:10]}.png"
            filepath = GENERATED_DIR / filename
            img.save(filepath, "PNG")
        except:
            image_bytes = None
    if not filepath:
        filepath = generate_fallback(req.prompt, req.size)
    return {"success": True, "filename": filepath.name, "url": f"/generated/{filepath.name}", "prompt": full_prompt, "used_fallback": not image_bytes}

@app.get("/api/history")
async def get_history():
    files = sorted([f for f in GENERATED_DIR.iterdir() if f.suffix == ".png"], key=lambda f: f.stat().st_mtime, reverse=True)
    return {"files": [{"filename": f.name, "url": f"/generated/{f.name}"} for f in files[:50]]}

@app.get("/api/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("Game Asset Gen - http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
