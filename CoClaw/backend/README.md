# CoClaw Backend

轻量 API 服务（FastAPI）用于承载 CoClaw 控制面。

## 启动

```bash
cd CoClaw/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 18080
```

健康检查：`GET http://localhost:18080/healthz`
