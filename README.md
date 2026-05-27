# Game Asset Gen

AI 2D Game Asset Generator - 七牛云 XEngineer 暑期实训营项目

## 功能

- 文本生成 2D 游戏素材（角色/场景/道具/UI/Tileset）
- 多种风格：像素风、卡通风、日式RPG
- 多种尺寸：16x16 到 512x512
- 自动透明背景处理
- 一键下载 PNG

## 技术栈

- 后端: Python FastAPI
- 前端: HTML + Tailwind CSS
- AI 生图: HuggingFace Inference API (Flux-2D-Game-Assets-LoRA)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py

# 访问
# http://localhost:8000
```

## API

- `POST /api/generate` - 生成素材
- `GET /api/history` - 获取历史
- `GET /api/health` - 健康检查

## 项目结构

```
game-asset-gen/
├── main.py           # FastAPI 后端
├── requirements.txt  # 依赖
├── static/
│   └── index.html    # 前端页面
└── generated/        # 生成的图片
```
