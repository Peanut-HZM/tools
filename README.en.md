# Toolbox - Full-Stack Tool Aggregation Platform

A comprehensive collection of practical tools covering AI chat, file processing, development utilities, and system management. Built with a separated frontend-backend architecture, supporting both Web and Mini Program access.

[中文文档](README.md) | **English**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?style=flat-square&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-3+-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)

## 📖 Introduction

This project is a feature-rich full-stack tool aggregation platform providing 25+ practical tools, including AI chat, image/video generation, OCR text recognition, ASR speech recognition, database management, SSH terminal, K8s console, and more. It supports enterprise-level features such as file storage (MinIO/Alibaba Cloud OSS), user authentication, and token usage statistics.

## ✨ Features

### 🤖 AI & Smart Tools
- **AI Assistant** - Multi-model conversation with context management
- **Image Generation** - Support for multiple AI image generation models
- **Video Generation** - AI video creation tool
- **Product Manager Agent** - LLM-driven PRD generation

### 📝 Document & File Processing
- **Markdown Editor** - File tree management, real-time preview, full-text search
- **MarkItDown Converter** - Multi-format document conversion
- **JSON Formatter** - JSON beautification and validation
- **Image Downloader** - Batch image downloading

### 🔍 Recognition & Conversion
- **OCR** - Text extraction from images
- **ASR** - Speech-to-text conversion

### 💻 Development Tools
- **HTTP API Client** - API debugging and testing
- **Database Tool** - Online SQL execution and data management
- **Redis Tool** - Redis data browsing and management
- **SSH Terminal** - Remote server connection
- **Key Generator** - Random key/token generation
- **K8s Console** - Kubernetes cluster management

### 🌐 Other Tools
- **Calendar** - Schedule management
- **System Monitor** - Service status monitoring
- **Token Usage Statistics** - AI API call tracking
- **Learning Share Platform** - Course and knowledge sharing
- **OpenClaw Chat** - Gateway conversation service
- **Video Downloader** - Video content downloading
- **Cross Share** - Cross-platform file sharing

### 🎨 General Features
- 🌓 **Light/Dark Theme** - Switch between light and dark modes
- 🔍 **Smart Search** - Real-time tool search with debounce optimization
- 🏷️ **Category Filter** - Multiple tool categories for quick navigation
- 📱 **Responsive Layout** - Perfect adaptation for desktop, tablet, and mobile
- 📱 **Mini Program Support** - Taro cross-platform mini program
- 🔐 **User Authentication** - JWT authentication system
- 👤 **User Isolation** - Independent file storage for each user

## 🔧 Configuration (Must Read Before First Run)

### 1. Copy Configuration Files

```bash
# Backend configuration (required)
cd backend
cp .env.example .env
# Edit .env, fill in JWT secret, database, storage configs as needed

# Frontend configuration (optional, use defaults for development)
cd ../frontend
cp .env.example .env
```

### 2. Generate Security Keys (Required for Production)

```bash
cd backend
python scripts/generate_keys.py
# Fill the generated keys into JWT_SECRET_KEY and DB_ENCRYPTION_KEY in backend/.env
```

### 3. Start Services

```bash
cd ..
python dev-services.py
```

> **Note**: Services can start with default configuration, but unconfigured features (OSS/MinIO storage, OCR, ASR, etc.) will not be available.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (optional, SQLite by default)
- Redis (optional, for token usage caching)

### One-Click Startup

**Recommended: Use dev-services.py to manage services (easiest):**

```bash
# Start frontend and backend services
python dev-services.py

# Check service status
python dev-services.py status

# Restart services
python dev-services.py restart

# Stop services
python dev-services.py stop

# View real-time logs
python dev-services.py logs backend
python dev-services.py logs frontend
```

**Traditional Method (Manual Startup):**

1. **Start Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 19092
# Windows alternative: python -m uvicorn app.main:app --reload --port 19092
```

2. **Start Frontend**
```bash
cd frontend
npm install
npm run dev
```

3. **Access Application**
Open browser and visit http://localhost:5178

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.10+
- **ORM**: SQLAlchemy 2.0
- **Validation**: Pydantic v2
- **Server**: Uvicorn
- **Database**: PostgreSQL / SQLite
- **Cache**: Redis
- **Storage**: MinIO / Alibaba Cloud OSS
- **API Docs**: Swagger UI / ReDoc

### Frontend
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Icons**: Font Awesome
- **HTTP Client**: Axios

### Mini Program
- **Framework**: Taro 4.x
- **Language**: TypeScript + React
- **Styling**: Sass

## 📁 Project Structure

```
tools/
├── backend/                    # Python backend service
│   ├── app/
│   │   ├── main.py            # FastAPI application entry
│   │   ├── api/routes/        # API v1 routes
│   │   ├── routes/            # Tool routes (OCR, ASR, SSH, K8s, etc.)
│   │   ├── models/            # SQLAlchemy data models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic layer
│   │   ├── config/            # Configuration management
│   │   └── utils/             # Utility functions
│   ├── scripts/               # Backend scripts (key generation, etc.)
│   ├── tests/                 # Backend tests
│   ├── alembic/               # Database migrations
│   └── requirements.txt       # Python dependencies
├── frontend/                   # React frontend application
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Tools/         # Tool page implementations
│   │   │   └── Admin/         # Admin dashboard
│   │   ├── hooks/             # Custom hooks
│   │   ├── services/          # API service layer
│   │   ├── stores/            # Zustand state management
│   │   ├── types/             # TypeScript types
│   │   └── App.tsx            # Main application component
│   ├── scripts/               # Frontend scripts
│   └── package.json           # Node dependencies
├── mini-program/               # Taro mini program
│   ├── src/                   # Mini program source
│   ├── config/                # Mini program configuration
│   └── package.json           # Mini program dependencies
├── scripts/                    # Deployment & operations scripts
├── tests/                      # Integration tests
├── dev-services.py             # Service management script
├── deploy.py                   # Deployment script
├── deploy.env.example          # Deployment configuration example
├── README.md                   # Project documentation (Chinese)
├── README.en.md                # Project documentation (English)
├── CLAUDE.md                   # Claude Code configuration
└── AGENTS.md                   # AI Agent configuration
```

## 📚 API Documentation

After starting the backend service, visit:
- Swagger UI: http://localhost:19092/docs
- ReDoc: http://localhost:19092/redoc

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📦 Deployment

### Requirements

- Server: Linux / macOS / Windows
- Database: PostgreSQL 12+ (recommended) or SQLite
- Cache: Redis 6+ (optional)
- Storage: MinIO or Alibaba Cloud OSS

### Deployment Steps

1. Copy `deploy.env.example` to `deploy.env` and configure server information
2. Run `python deploy.py` for automated deployment
3. Or refer to `local_deploy.sh` for manual deployment

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome!

## 📄 License

© 2024-2026. All rights reserved.
