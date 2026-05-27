"""
game-asset-gen - AI 2D Game Asset Generator
FastAPI backend - Route C: Sprite Sheet via pure prompt (no img2img)
全部帧用 Tongyi-MAI/Z-Image-Turbo 生成，靠强 prompt 约束角色一致性
成本: ¥0.30/次 (4帧)
"""
import io
import json
import os
import ssl
import time
import uuid
from pathlib import Path
from typing import List
import urllib.request
import base64

import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

# ─── Configuration ────────────────────────────────────────────────────────────
SF_API_URL   = "https://api.siliconflow.cn/v1/images/generations"
SF_API_KEY   = os.environ.get("SF_API_KEY", "sk-qldnafwtngpczmpvxbiwezsdwvpqhenneptfdbnqutwghkxx")
MODEL_REF    = "Tongyi-MAI/Z-Image-Turbo"
SSL_CTX      = ssl.create_default_context()
GENERATED_DIR = Path("generated")
GENERATED_DIR.mkdir(exist_ok=True)
EXECUTOR    = ThreadPoolExecutor(max_workers=4)

# ─── Prompt 模板 ─────────────────────────────────────────────────────────────
# Route C: 纯 prompt，每帧都要包含角色特征描述（无参考图）
FRAME_TEMPLATES = {
    "idle":   "pixel art game sprite, {char} {desc}, front view, idle standing pose, arms relaxed, {colors}, transparent background, {size}-bit RPG style, same character across all frames",
    "walk":   "pixel art game sprite, {char} {desc}, front view, walking pose, left foot forward, {colors}, transparent background, {size}-bit RPG style, same character as idle frame",
    "attack": "pixel art game sprite, {char} {desc}, front view, attacking pose, sword raised high, {colors}, transparent background, {size}-bit RPG style, same character as idle frame",
    "cast":   "pixel art game sprite, {char} {desc}, front view, casting spell pose, both hands raised up, {colors}, transparent background, {size}-bit RPG style, same character as idle frame",
}

STYLE_COLORS = {
    "pixel":   "pixel art palette, limited colors, 8-bit to 16-bit style",
    "cartoon": "cartoon style, vibrant saturated colors",
    "jp_rpg":  "Japanese SNES RPG style, soft shading",
}

SIZE_MAP = {
    "16x16": (16, 16), "32x32": (32, 32), "64x64": (64, 64),
    "128x128": (128, 128), "256x256": (256, 256), "512x512": (512, 512),
}
FRAME_ORDER = ["idle", "walk", "attack", "cast"]

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(title="Game Asset Gen - Sprite Sheet (Route C)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static",    StaticFiles(directory="static"),    name="static")
app.mount("/generated", StaticFiles(directory="generated"), name="generated")

class GenerateRequest(BaseModel):
    prompt: str
    asset_type: str = "character"
    style: str = "pixel"
    size: str = "128x128"

class SpriteSheetRequest(BaseModel):
    prompt: str
    style: str = "pixel"
    size: str = "64x64"

# ─── 核心 API 调用 ────────────────────────────────────────────────────────────

def _call_sf(prompt: str) -> bytes:
    """调用 SiliconFlow 文生图（纯 text2img，无 img2img）。"""
    data = json.dumps({
        "model": MODEL_REF,
        "prompt": prompt,
        "image_size": "512x512",
    }).encode("utf-8")
    headers = {"Authorization": f"Bearer {SF_API_KEY}", "Content-Type": "application/json"}
    for attempt in range(3):
        try:
            req = urllib.request.Request(SF_API_URL, data=data, method="POST")
            for k, v in headers.items():
                req.add_header(k, v)
            r = urllib.request.urlopen(req, timeout=40, context=SSL_CTX)
            resp = json.loads(r.read().decode())
            img_url = resp["images"][0]["url"]
            return urllib.request.urlopen(
                urllib.request.Request(img_url), timeout=20, context=SSL_CTX
            ).read()
        except Exception as e:
            print(f"[SF] attempt {attempt+1} error: {e}")
            if attempt < 2:
                time.sleep(5)
    return None

def remove_bg_simple(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    data = img.getdata()
    new_data = [
        (255, 255, 255, 0) if (r > 230 and g > 230 and b > 230) else (r, g, b, a)
        for r, g, b, a in data
    ]
    img.putdata(new_data)
    return img

def resize_image(img: Image.Image, size_str: str) -> Image.Image:
    target = SIZE_MAP.get(size_str, (64, 64))
    return img.convert("RGBA").resize(target, Image.NEAREST)

def build_sprite_prompt(prompt: str, frame: str, style: str, size_str: str) -> str:
    """为指定帧构建完整 prompt（纯文字，无参考图）。"""
    bit   = size_str.split("x")[0]
    colors = STYLE_COLORS.get(style, STYLE_COLORS["pixel"])
    parts = prompt.strip().split(maxsplit=1)
    char  = parts[0]
    desc  = parts[1] if len(parts) > 1 else ""
    tmpl  = FRAME_TEMPLATES.get(frame, FRAME_TEMPLATES["idle"])
    return tmpl.format(char=char, desc=desc, colors=colors, size=bit)

# ─── Routes ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/generate")
async def generate_asset(req: GenerateRequest):
    PROMPT_TEMPLATES = {
        "character": "pixel art game sprite of {prompt}, standing pose, front view, transparent background, 16-bit RPG style, game asset",
        "scene":     "pixel art game background, {prompt}, top-down view, 16-bit RPG style, game environment asset",
        "item":      "pixel art game item icon, {prompt}, centered, transparent background, 16-bit RPG style, game asset",
        "ui":        "pixel art game UI element, {prompt}, clean design, 16-bit RPG style, transparent background",
        "tileset":   "pixel art game tileset, {prompt}, seamless tileable, top-down view, 16-bit RPG style",
    }
    STYLE_SUFFIX = {
        "pixel": "pixel art style, 8-bit to 16-bit",
        "cartoon": "cartoon style, vibrant colors",
        "jp_rpg":  "Japanese RPG style, SNES aesthetic",
    }
    template = PROMPT_TEMPLATES.get(req.asset_type, PROMPT_TEMPLATES["character"])
    style_s   = STYLE_SUFFIX.get(req.style, "")
    full_prompt = f"{template.format(prompt=req.prompt)}, {style_s}".strip(", ")

    image_bytes = _call_sf(full_prompt)
    filepath = None
    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = resize_image(img, req.size)
            img = remove_bg_simple(img)
            filename = f"asset_{uuid.uuid4().hex[:10]}.png"
            filepath  = GENERATED_DIR / filename
            img.save(filepath, "PNG")
        except Exception as e:
            print(f"Img process error: {e}")
    if not filepath:
        w, h = SIZE_MAP.get(req.size, (128, 128))
        colors = [(60, 120, 200), (200, 80, 80), (80, 180, 80), (180, 140, 50)]
        color  = colors[abs(hash(req.prompt)) % len(colors)]
        img    = Image.new("RGBA", (w, h), (*color, 255))
        filename = f"fallback_{uuid.uuid4().hex[:8]}.png"
        filepath  = GENERATED_DIR / filename
        img.save(filepath, "PNG")
    return {
        "success": True,
        "filename": filepath.name,
        "url": f"/generated/{filepath.name}",
        "prompt": full_prompt,
        "used_fallback": not bool(image_bytes),
    }

# Sprite Sheet 生成（Route C：纯 prompt，无 img2img）
@app.post("/api/generate-spritesheet")
async def generate_spritesheet(req: SpriteSheetRequest):
    """Sprite Sheet 生成（Route C：纯 prompt，成本低但角色一致性有限）。
    同步 API 调用放到线程池，避免阻塞 FastAPI 事件循环。
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        EXECUTOR, _generate_spritesheet_sync, req.prompt, req.style, req.size
    )
    return result

def _generate_spritesheet_sync(prompt: str, style: str, size_str: str):
    size_str = size_str or "64x64"
    w, h     = SIZE_MAP.get(size_str, (64, 64))

    # 4 帧全部用纯 prompt 生成（无参考图）
    frames: List[Image.Image] = []
    frame_errors = 0
    prompts_used = []

    for frame_name in FRAME_ORDER:
        frame_prompt = build_sprite_prompt(prompt, frame_name, style, size_str)
        prompts_used.append(frame_prompt)
        fb = _call_sf(frame_prompt)
        if not fb:
            frame_errors += 1
            frames.append(Image.new("RGBA", (w, h), (100, 100, 100, 255)))
        else:
            try:
                img = Image.open(io.BytesIO(fb)).convert("RGBA")
                img = resize_image(img, size_str)
                img = remove_bg_simple(img)
                frames.append(img)
            except:
                frames.append(Image.new("RGBA", (w, h), (100, 100, 100, 255)))

    # 拼接为 Sprite Sheet（2行×2列）
    sheet_w = w * 2
    sheet_h = h * 2
    sheet   = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    for i, frame_img in enumerate(frames):
        col = i % 2
        row = i // 2
        sheet.paste(frame_img, (col * w, row * h), frame_img)

    filename = f"sprite_{uuid.uuid4().hex[:10]}.png"
    filepath  = GENERATED_DIR / filename
    sheet.save(filepath, "PNG")

    # 各帧单独保存
    frame_urls = []
    for i, frame_img in enumerate(frames):
        fn = f"frame_{uuid.uuid4().hex[:6]}_{FRAME_ORDER[i]}.png"
        frame_img.save(GENERATED_DIR / fn, "PNG")
        frame_urls.append(f"/generated/{fn}")

    return {
        "success": True,
        "filename": filename,
        "url": f"/generated/{filename}",
        "frames": frame_urls,
        "frame_names": FRAME_ORDER,
        "size": size_str,
        "layout": "2x2",
        "used_img2img": False,
        "used_fallback": frame_errors > 0,
        "route": "C - pure prompt (no img2img)",
        "prompts_used": prompts_used,
    }

@app.get("/api/history")
async def get_history():
    files = sorted(
        [f for f in GENERATED_DIR.iterdir() if f.suffix == ".png"],
        key=lambda f: f.stat().st_mtime, reverse=True
    )
    return {"files": [{"filename": f.name, "url": f"/generated/{f.name}"} for f in files[:50]]}

@app.get("/api/health")
async def health():
    return {"status": "ok", "route": "C - pure prompt sprite sheet"}

if __name__ == "__main__":
    import uvicorn
    print("Game Asset Gen [Route C - Pure Prompt] - http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
