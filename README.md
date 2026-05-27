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
- AI 生图: **SiliconFlow** (通义万相 Tongyi-MAI/Z-Image-Turbo)

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 SiliconFlow API Key（可选，默认使用内置 key）
# Windows
set SF_API_KEY=sk-your-api-key
# macOS/Linux
export SF_API_KEY=sk-your-api-key

# 运行
python main.py

# 访问
# http://localhost:8000
```

> SiliconFlow 注册地址: https://cloud.siliconflow.cn

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

## 技术说明

- 使用 `urllib` 而非 `httpx` 调用 API，兼容 Python 3.8 环境下的 SSL 问题
- 生成后自动 resize 到用户选择的尺寸（使用 PIL NEAREST 缩放保留像素感）
- 生成后自动简单去背（白色背景转透明）
- API 调用失败时自动降级为彩色格子占位图
