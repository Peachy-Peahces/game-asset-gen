# Game Asset Gen

AI 2D 游戏素材生成器 — 七牛云 XEngineer 暑期实训营

## 功能

### 单图生成
- 文本 → 2D 游戏素材（角色/场景/道具/UI/Tileset）
- 风格：像素风 · 卡通风 · 日式RPG
- 尺寸：16×16 到 512×512
- 自动透明背景 + PNG 下载

### Sprite Sheet 多帧动画（新增）
- 4 帧动画：待机 / 走路 / 攻击 / 施法
- **2×2 排列**，可直入 Unity/Godot/Cocos
- 两条技术路线（见下方）

---

## Sprite Sheet 两条路线

| | 路线 B（生产推荐） | 路线 C（成本优先） |
|---|---|---|
| **方案** | 参考图 + img2img | 纯 prompt |
| **模型** | Z-Image-Turbo + Qwen-Image-Edit | 全部 Z-Image-Turbo |
| **角色一致性** | ✅ 好 | ⚠️ 一般 |
| **成本** | ¥1.50 / 次 | ¥0.30 / 次 |
| **生成时间** | ~2.5 分钟 | ~1 分钟 |
| **分支** | `feature/sprite-sheet-img2img` | `feature/sprite-sheet-prompt` |

---

## 快速开始

```bash
pip install -r requirements.txt
python main.py
# 访问 http://localhost:8000
```

> SiliconFlow 注册: https://cloud.siliconflow.cn  
> SiliconFlow API Key: `sk-qldnafwtngpczmpvxbiwezsdwvpqhenneptfdbnqutwghkxx`（内置）

---

## API

| 端点 | 说明 |
|---|---|
| `POST /api/generate` | 单图生成 |
| `POST /api/generate-spritesheet` | Sprite Sheet 生成（4帧） |
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

- **Python 3.8 兼容**: 用 `urllib` + `ThreadPoolExecutor` 替代 `httpx` + `asyncio.to_thread`
- **去背**: 简单阈值法（白色→透明），浅色背景可能残留
- **降级**: API 失败时自动生成彩色格子占位图
- **前端**: 两个 Tab（单图 / Sprite Sheet），历史记录自动刷新
