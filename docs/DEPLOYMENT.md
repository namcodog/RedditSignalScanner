# Reddit Signal Scanner – 部署手册 (Day 11)

## 1. 文档范围
- **来源**: `docs/PRD/ARCHITECTURE.md`、`docs/PRD/PRD-04-任务系统.md`、`docs/PRD/PRD-07-Admin后台.md`
- **目标交付**: Day 11 Backend B 任务“文档完善 + 部署准备”（`reports/phase-log/DAY10-12-EXECUTION-CHECKLIST.md`）
- **读者**: DevOps / Backend B 在 Day 11-12 完成演练并交付给 Lead 验收

## 2. 环境要求
| 角色 | 版本/说明 |
| --- | --- |
| OS | Linux (Ubuntu 22.04) / macOS 14 | 
| Python | 3.11.x | 
| Node.js | 18.x (LTS) | 
| PostgreSQL | 15.x (含 `uuid-ossp` 扩展) | 
| Redis | 7.0+ | 
| Celery | 5.3.x（随代码部署） | 
| Nginx | 1.24+ (可选，用于TLS) | 
| pm2 / systemd | 前端/后端常驻 (二选一) | 

> **检查脚本**: `make env-check`，若某依赖缺失，请先完成 `docs/2025-10-10-环境配置完全指南.md` 中的安装步骤。

## 3. 预部署清单
- PRD 全量通过 (参考 `reports/phase-log/DAY10-FINAL-ACCEPTANCE-REPORT.md`)
- Admin E2E (`make test-admin-e2e`) 已通过，`ADMIN_EMAILS` 已配置
- 数据库迁移已打包 (Alembic head)
- `.env.production`. 已对齐安全配置 (JWT_SECRET、ADMIN_EMAILS、DATABASE_URL 等)
- Redis 与 Celery 运行用户已创建并最小权限化
- 监控/告警渠道已准备 (Slack/Email)

## 4. 部署流程

### Step 1: 拉取源码
```bash
git clone <repo>
cd RedditSignalScanner
git checkout release/day11
```

### Step 2: 配置环境变量
```bash
cp .env.example .env.production
vi .env.production
# 必需:
# DATABASE_URL=postgresql+psycopg://user:pass@db-host:5432/reddit_scanner
# REDIS_URL=redis://redis-host:6379/0
# JWT_SECRET=<随机32字节>
# ADMIN_EMAILS=devops@example.com
# FRONTEND_BASE_URL=https://app.example.com
```

### Step 3: 数据库迁移
```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

### Step 4: 后端部署
- 推荐使用 `uvicorn` + `systemd` (单实例) 或 `gunicorn` (多实例)
- 示例 systemd 单元:
```
/etc/systemd/system/rss-backend.service

[Unit]
Description=Reddit Signal Scanner Backend (Day11)
After=network.target

[Service]
User=deploy
WorkingDirectory=/opt/rss/backend
EnvironmentFile=/opt/rss/.env.production
ExecStart=/opt/rss/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8006
Restart=always

[Install]
WantedBy=multi-user.target
```
- 启动命令:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rss-backend
```

### Step 5: Celery Worker
```
/etc/systemd/system/rss-celery.service

[Unit]
Description=RSS Celery Worker
After=network.target

[Service]
User=deploy
WorkingDirectory=/opt/rss/backend
EnvironmentFile=/opt/rss/.env.production
ExecStart=/opt/rss/backend/venv/bin/celery -A app.tasks.analysis_tasks worker --loglevel=info --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```
启动: `sudo systemctl enable --now rss-celery`

### Step 6: 前端构建与发布
```bash
cd frontend
npm ci
npm run build
# 输出: dist/
```
> 选项 A: 使用 Nginx serve -> 将 `dist/` 拷贝到 `/var/www/rss`，配置静态站点
> 选项 B: 使用 Vercel/Netlify → 上传 dist

### Step 7: 反向代理/Nginx (可选)
```
server {
  listen 80;
  server_name app.example.com;

  location /api/ {
    proxy_pass http://127.0.0.1:8006/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location / {
    root /var/www/rss;
    try_files $uri /index.html;
  }
}
```

### Step 8: 验证
| 项目 | 命令 | 目标 |
| --- | --- | --- |
| 健康检查 | `curl http://localhost:8006/api/healthz` | `{"status":"ok"}` |
| 后端日志 | `journalctl -u rss-backend -f` | 无 ERROR |
| Celery Worker | `celery -A app.core.celery_app.celery_app inspect active` | 至少 1 worker |
| 管理端测试 | `make test-admin-e2e` (在部署机上) | 通过 |
| 前端访问 | 浏览器打开 `https://app.example.com` | UI加载成功 |


## 5. 回滚策略
1. `sudo systemctl stop rss-backend rss-celery`
2. `git checkout` 回滚到上一发行版本
3. 重新构建前端并反向部署
4. 如涉及数据库，执行 `alembic downgrade <prev>` （确保 migrations 可逆）

## 6. 部署 Checklist (给 Lead/QA)
- [ ] `.env.production` 与 PRD 配置一致
- [ ] PostgreSQL 连接通过 (`python backend/verify_db.py`)
- [ ] Redis 连接通过 (`redis-cli ping`)
- [ ] 后端服务 & Celery 常驻
- [ ] Admin Dashboard 正常访问
- [ ] `make test-e2e` / `make test-admin-e2e` 均通过
- [ ] 监控项启用（Redis/Celery/PostgreSQL 指标收集）
- [ ] 部署报告已记录于 `reports/phase-log/`

---
**文档状态**: Draft Day 11 – 待 Frontend/QA 使用验证后在 Day 12 更新。
