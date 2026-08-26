# 旧公开 aiolanbon → LOIP 1.0.0 迁移清单

基线：公司 `lanbon/aiolanbon` main `7d35902fc3ff40d399c11e1533d2e32a23333a85`  
公开来源提交：`cee778c9d69ed5dbe09068c179ab6f1b2579c54e`（Initial aiolanbon 0.1.0）  
协议：`lanbon/loip-protocol` 标签 `v1.0.0-internal.1` → commit `c24f7cdacfee9e2e89d57ce40c84b5c242013680`  
优先级：冻结 LOIP > 第4期实机行为 > 旧代码。旧代码可运行不能绕过协议。

## 保留

| 旧路径 / 提交 | 原因 |
|---|---|
| git 历史（cee778c → 7d35902） | 公开源码与来源提交可追溯 |
| 包名 `aiolanbon`、`src/` 布局、setuptools | 工程骨架 |
| `LICENSE` | 许可不变 |
| `.gitignore` 对 dist/build/venv | 构建物不进 git |
| `aiohttp` 异步 HTTP | 继续作为传输 |
| 构造顺序 `(host, port, token, session)`、默认端口 8765 | 调用约定 |
| HTTP Bearer Header 雏形 `_headers()` | 鉴权方式正确，仅补全规则 |
| `LanbonClient` / `LanbonError` 名称 | 给第6期 HA 当唯一通信依赖，不在本期写 HA |

## 重写

| 旧路径 | 新路径 | 原因 |
|---|---|---|
| `src/aiolanbon/client.py` | `client.py` + `models.py` + `_redact.py` | 旧 WS 为 `/api/v1/ws?token=`，违反冻结协议 |
| `src/aiolanbon/exceptions.py` | `exceptions.py` | 旧错误看 `err` 字符串；协议为 `error.code` + HTTP 401/429/超时 |
| `src/aiolanbon/__init__.py` | `__init__.py` | 导出模型、标准错误、发现解析 |
| `pyproject.toml` | `pyproject.toml` | 去掉 Home Assistant 关键词与公开 GitHub 地址；加测试/打包 |
| `README.md` | `README.md` | 按 LOIP 1.0.0 说明，示例不含真实 Token |

重写覆盖：`GET /info`、`GET /devices`（revision/ETag/304）、组件 capabilities（features/commands/constraints）、`POST /command`、`GET /api/v1/events`（Header 鉴权）、轮询回退、重连退避、日志/异常脱敏。

## 删除（不得再出现在库行为中）

| 旧行为 / 配置 | 原因 |
|---|---|
| `ws://…/api/v1/ws?token=` | Token 进 URL；路径不是 `/api/v1/events` |
| 命令失败解析 `data["err"]` | 非冻结字段 |
| `keywords = ["homeassistant"]` 与 GitHub homepage | 本期库不得依赖 HA、不得指向公开 GitHub 发布面 |
| 按 `series`/`model`/`L8`/`L9`/`L10` 判断能力 | 能力只看 component 声明 |
| 把 Token 写入 mDNS TXT 或从 TXT 读取 Token | 安全规范禁止 |
| 协议包、L10 固件、HA 集成、实机 log、sdist/wheel | 不得进本仓库 |

## 不在本期

Home Assistant 集成、config flow、实体矩阵、PyPI/公开 GitHub/公司标签/Release、L8/L9 固件。
