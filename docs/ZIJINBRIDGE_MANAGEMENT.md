# 紫金桥跨平台实时数据库管理工具

本模块把 FastapiAdmin 扩展为一个面向紫金桥®跨平台实时数据库 REST API 的管理控制台。目标不是重写紫金桥 REST Service，而是提供一个带 FastapiAdmin 登录/RBAC、防误操作、批量查询、分片、导出和可视化工作流的管理层。

## 1. 功能范围

| 功能 | 紫金桥 REST API | FastapiAdmin 管理端 |
| --- | --- | --- |
| REST 连通性/登录 | `/api/realdir`、`/api/userlogin`、`/api/userlogout` | 连接检测、登录/登出、浏览器会话 token |
| 对外发布目录 | `/api/realdir/{node...}` | 树形浏览、节点选择 |
| 节点实时数据 | `/api/realdata/{node...}` | 递归加载点位、表格多选 |
| 实时批量取值 | `/api/realdata?names=...` | 批量查询、1/2/5/10 秒轮询 |
| 注册项快速取值 | `/api/realdata?regname=...` | 点组注册、按注册名快速读取 |
| 实时写入 | `POST /api/realdata` | JSON 批量写入 + 二次确认 + RBAC |
| 多时间点历史 | `/api/hisdata?times=...&names=...` | 批量点位、多个时间点、自动拆批 |
| 时间范围历史 | `/api/hisdata?startTime=...&endTime=...&interval=...` | 时间选择、采样间隔、自动时间切片 |
| 历史写入 | `POST /api/hisdata` | JSON 批量写入 + 二次确认 + RBAC |
| 历史导出 | 上述历史接口 | CSV / XLSX，自动恢复 valueonly 时间轴 |
| SQL | `POST /api/SQL` | SQL 控制台，默认只读；写 SQL 需服务端显式解锁 |
| 报警 | `/api/alarmdata` | 实时/历史报警、级别/点位筛选、CSV/XLSX |

## 2. 页面入口

程序启动后会幂等创建：

- `工业数据`
  - `紫金桥管理`
    - 查询权限：`module_zijinbridge:query`
    - 数据写入权限：`module_zijinbridge:write`
    - SQL 控制台权限：`module_zijinbridge:sql`

`SUPER_ADMIN` 与 `ADMIN` 角色会自动获得这些菜单/权限。已有在线用户合并升级后需要重新登录一次，刷新 Redis 中的权限会话。

前端组件：

```text
frontend/web/src/views/module_zijinbridge/index.vue
```

后端代理 API：

```text
/api/v1/industrial/zijinbridge/*
```

## 3. 历史数据批量查询策略

紫金桥服务自身会限制单次查询/插入量。管理端因此不把“100 个点 × 一整天 × 250 ms”直接塞进一个 HTTP 请求，而是按两个维度切片：

1. **点位切片**：`names_per_request`，默认每批 50 个点；
2. **时间切片**：
   - `times` 模式按 `samples_per_request` 拆分离散时间点；
   - `range` 模式按 `interval × samples_per_request` 计算时间窗。

各分片完成后，后端按原始点位顺序合并。这样用户仍只操作一次“查询/导出”，但不会轻易触发紫金桥单次数据量上限。

### 示例：时间范围 + 间隔

```json
{
  "base_url": "http://127.0.0.1:8000",
  "mode": "range",
  "names": ["A1.PV", "A2.DESC"],
  "start_time": "2026-09-08T10:00:00.000",
  "end_time": "2026-09-08T11:00:00.000",
  "interval": 1000,
  "value_only": true,
  "names_per_request": 50,
  "samples_per_request": 5000
}
```

### 示例：多个指定时间点

```json
{
  "base_url": "http://127.0.0.1:8000",
  "mode": "times",
  "names": ["A1.PV", "A2.DESC"],
  "times": [
    "2022-02-22T14:22:33.444",
    "2022-02-22T15:22:34.555"
  ],
  "value_only": false
}
```

## 4. 配置

以下均为可选环境变量：

```env
# 访问紫金桥单个分片的 HTTP 超时（秒）
ZIJINBRIDGE_TIMEOUT=30

# 单次管理端逻辑查询最多合并的数据单元（点位数 × 时间点数）
ZIJINBRIDGE_MAX_QUERY_CELLS=2000000

# 历史/报警 CSV/XLSX 最大导出行数
ZIJINBRIDGE_MAX_EXPORT_ROWS=2000000

# 默认 0：只允许 localhost、loopback、private/link-local 地址。
# 只有确需连接公网紫金桥时才设置为 1。
ZIJINBRIDGE_ALLOW_PUBLIC_HOSTS=0

# 默认 0：SQL 控制台禁止写 SQL。
# 即使前端关闭“只读保护”，服务端仍需显式设置 1 才允许非查询语句。
ZIJINBRIDGE_ALLOW_SQL_WRITE=0
```

> 推荐让 FastapiAdmin 与紫金桥 REST Service 位于同机或受控内网，不建议把紫金桥 REST Service 本身直接暴露到公网。
>
> 如果紫金桥侧启用了 REST 缓存，需要特别注意官方手册对该模式的提示：实时数据会从发布项缓存直接返回，因此应把“对外发布数据项”本身当作安全边界，严格控制发布点范围，并配合网络隔离。

## 5. 凭据与安全设计

- 紫金桥用户名/密码只用于一次 `/login` 代理请求，不写数据库、不写 FastapiAdmin 操作日志。
- 紫金桥 token 由前端保存在 `sessionStorage`，通过 `X-Zijin-Token` 传给 FastapiAdmin；代理到紫金桥时再按官方接口要求放入 URL 查询参数。
- 管理端默认拒绝把代理目标指向公网主机，降低 SSRF 风险。
- 实时/历史写入需要 `module_zijinbridge:write`。
- SQL 需要独立 `module_zijinbridge:sql` 权限；此外服务端默认仅接受可解析为查询语句的 SQL。
- 实时/历史写入页面均有二次确认。
- 管理端不会尝试实现官方 REST 文档中不存在的“报警确认/禁止”写入接口。

## 6. REST 代理接口

### 连接与目录

```text
POST /api/v1/industrial/zijinbridge/status
POST /api/v1/industrial/zijinbridge/login
POST /api/v1/industrial/zijinbridge/logout
POST /api/v1/industrial/zijinbridge/directory?node_path=root/group1
POST /api/v1/industrial/zijinbridge/points
```

### 实时数据

```text
POST /api/v1/industrial/zijinbridge/realtime/query
POST /api/v1/industrial/zijinbridge/realtime/register
POST /api/v1/industrial/zijinbridge/realtime/registered
POST /api/v1/industrial/zijinbridge/realtime/write
```

### 历史数据

```text
POST /api/v1/industrial/zijinbridge/history/query
POST /api/v1/industrial/zijinbridge/history/export
POST /api/v1/industrial/zijinbridge/history/write
```

### 报警 / SQL

```text
POST /api/v1/industrial/zijinbridge/alarms/query
POST /api/v1/industrial/zijinbridge/alarms/export
POST /api/v1/industrial/zijinbridge/sql/query
```

## 7. 本地验证

后端：

```bash
cd backend
uv sync
uv run pytest tests/test_zijinbridge_service.py -q
uv run ruff check app/modules/zijinbridge tests/test_zijinbridge_service.py
```

前端：

```bash
cd frontend/web
pnpm install
pnpm type-check
pnpm build
```

没有真实紫金桥服务时，后端单测会 mock 上游请求来验证分片、时间映射、SQL 保护与内网目标校验；端到端点值/报警验证仍需要一套可访问的紫金桥 REST Service。

## 8. 使用建议

1. 在紫金桥 IDE 中启用 REST Service，并优先启用安全管理。
2. 在“对外发布数据项”中只发布需要给管理端读取的点。
3. FastapiAdmin 中先“检测连接”，安全管理开启时再登录紫金桥。
4. 在节点树选择目录并“载入点位”，勾选后加入批量选择。
5. 历史查询优先使用 `valueonly` 处理大量数值点；需要明确每一条记录时间字符串时关闭它。
6. 大时间范围先提高 `interval`，再考虑调大每批时间点，避免紫金桥和浏览器同时承受过高数据量。
7. 写入、SQL 权限只授权给确实需要的管理员。
