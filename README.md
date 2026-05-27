# Game Asset Gen

AI 2D 游戏素材生成器 — 七牛云 XEngineer 暑期实训营

## 功能

### 单图生成
- 文本 → 2D 游戏素材（角色/场景/道具/UI/Tileset）
- 风格：像素风 · 卡通风 · 日式RPG
- 尺寸：16×16 到 512×512
- 自动透明背景 + PNG 下载

### Sprite Sheet 多帧动画（双模式）
- 4 帧动画：待机 / 走路 / 攻击 / 施法
- **2×2 排列**，可直入 Unity/Godot/Cocos
- **图生图模式**（推荐）：参考图 + img2img，角色一致性好
- **纯Prompt模式**（低成本）：纯文字 prompt，成本低

---

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置 API Key（必须）
# Windows PowerShell:
$env:SF_API_KEY="your-siliconflow-api-key"
# Linux/Mac:
export SF_API_KEY="your-siliconflow-api-key"

# 3. 启动服务
python main.py
# 访问 http://localhost:8000
```

> SiliconFlow 注册: https://cloud.siliconflow.cn

---

## API

| 端点 | 说明 |
|---|---|
| `POST /api/generate` | 单图生成 |
| `POST /api/generate-spritesheet` | Sprite Sheet 生成（支持 mode=img2img 或 mode=prompt） |
| `GET /api/history` | 历史记录 |
| `GET /api/health` | 健康检查 |

---

## 项目结构

```
game-asset-gen/
├── main.py              # FastAPI 后端（Python 3.8+）
├── requirements.txt
├── static/
│   └── index.html       # 前端（Tailwind CSS + Vanilla JS）
├── generated/           # 生成的图片
└── README.md
```

## 技术说明

- **双模式 Sprite Sheet**: 图生图（质量优先 ¥1.50/次）+ 纯Prompt（成本优先 ¥0.30/次）
- **Python 3.8 兼容**: 用 `urllib` + `ThreadPoolExecutor` 替代 `httpx` + `asyncio.to_thread`
- **去背**: 简单阈值法（白色→透明），浅色背景可能残留
- **降级**: API 失败时自动生成彩色格子占位图
- **前端**: 两个 Tab（单图 / Sprite Sheet），Sprite Sheet 内可选生成模式
