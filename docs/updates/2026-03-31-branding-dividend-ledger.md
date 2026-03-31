# 2026-03-31 品牌文案更新

## 变更

- 中文名称统一为：`息流账本`
- 英文名称统一为：`Dividend Ledger`
- 对外展示名称统一为：`息流账本 / Dividend Ledger`

## 更新范围

- `README.md`
- `README.en.md`
- `backend/app/core/config.py`
- `backend/app/__init__.py`
- `backend/app/api/routes.py`
- `frontend/index.html`
- `frontend/src/App.vue`
- `frontend/src/components/TopMenuBar.vue`
- `deploy/yield-ledger.service`
- `frontend/package.json`
- `frontend/package-lock.json`

## 说明

- 仓库地址、部署目录、Compose 服务名等技术 slug 暂未更名，避免影响现有 Git、PVE 和 Docker 部署流程。
- 导出文件前缀已从 `yield-ledger-*` 调整为 `dividend-ledger-*`。
- PVE 线上实例已同步，页面标题、OpenAPI 标题和 systemd 服务描述均已更新。
