from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query, Security, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.dependencies import AuthPermission

from .schema import (
    AlarmExportIn,
    AlarmQueryIn,
    ExportFormat,
    HistoryExportIn,
    HistoryQueryIn,
    HistoryWriteIn,
    LoginIn,
    LogoutIn,
    NodePointsQueryIn,
    RealDataQueryIn,
    RealDataWriteIn,
    RegisterPointsIn,
    RegisteredQueryIn,
    ServiceStatusOut,
    SqlQueryIn,
    ZijinConnection,
)
from .service import ZijinBridgeService

# 登录请求包含紫金桥口令，因此故意不使用 OperationLogRoute，避免业务操作日志记录敏感请求体。
ZijinBridgeRouter = APIRouter(prefix="/zijinbridge", tags=["紫金桥实时数据库"])

ZijinToken = Annotated[str | None, Header(alias="X-Zijin-Token")]
READ_PERMISSION = ["module_zijinbridge:query"]
WRITE_PERMISSION = ["module_zijinbridge:write"]
SQL_PERMISSION = ["module_zijinbridge:sql"]


@ZijinBridgeRouter.post("/login", summary="登录紫金桥 REST 服务", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def login_controller(payload: LoginIn) -> JSONResponse:
    data = await ZijinBridgeService.login(payload.base_url, payload.user, payload.password)
    return SuccessResponse(data=data, msg="紫金桥登录成功")


@ZijinBridgeRouter.post("/logout", summary="登出紫金桥 REST 服务", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def logout_controller(payload: LogoutIn, token: ZijinToken = None) -> JSONResponse:
    if not token:
        return SuccessResponse(data={"code": 0}, msg="当前没有紫金桥 token")
    data = await ZijinBridgeService.logout(payload.base_url, token)
    return SuccessResponse(data=data, msg="紫金桥登出成功")


@ZijinBridgeRouter.post("/status", summary="检测紫金桥 REST 服务", response_model=ResponseSchema[ServiceStatusOut], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def status_controller(payload: ZijinConnection, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.status(payload.base_url, token)
    return SuccessResponse(data=data, msg="连接检测完成")


@ZijinBridgeRouter.post("/directory", summary="获取对外发布数据项节点结构", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def directory_controller(payload: ZijinConnection, token: ZijinToken = None, node_path: Annotated[str, Query()] = "") -> JSONResponse:
    data = await ZijinBridgeService.realdir(payload.base_url, token, node_path)
    return SuccessResponse(data=data, msg="获取点位目录成功")


@ZijinBridgeRouter.post("/points", summary="获取节点下已发布点位", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def node_points_controller(payload: NodePointsQueryIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.node_points(
        payload.base_url,
        token,
        payload.node_path,
        recursion=payload.recursion,
        decimal=payload.decimal,
    )
    return SuccessResponse(data=data, msg="获取节点点位成功")


@ZijinBridgeRouter.post("/realtime/query", summary="批量获取实时数据", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def realtime_query_controller(payload: RealDataQueryIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.realdata(payload, token)
    return SuccessResponse(data=data, msg="获取实时数据成功")


@ZijinBridgeRouter.post("/realtime/register", summary="注册批量快速取值点名", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def realtime_register_controller(payload: RegisterPointsIn, token: ZijinToken = None) -> JSONResponse:
    if not token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="注册点名必须先登录紫金桥并携带 token")
    data = await ZijinBridgeService.register_points(payload, token)
    return SuccessResponse(data=data, msg="注册点名成功")


@ZijinBridgeRouter.post("/realtime/registered", summary="按注册项获取实时数据", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def realtime_registered_controller(payload: RegisteredQueryIn, token: ZijinToken = None) -> JSONResponse:
    if not token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="注册项取值必须携带紫金桥 token")
    data = await ZijinBridgeService.registered_realdata(payload, token)
    return SuccessResponse(data=data, msg="获取注册项实时数据成功")


@ZijinBridgeRouter.post("/realtime/write", summary="批量设置实时数据", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(WRITE_PERMISSION))])
async def realtime_write_controller(payload: RealDataWriteIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.write_realdata(payload, token)
    return SuccessResponse(data=data, msg="设置实时数据成功")


@ZijinBridgeRouter.post("/history/query", summary="批量查询历史数据", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def history_query_controller(payload: HistoryQueryIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.history(payload, token)
    return SuccessResponse(data=data, msg="获取历史数据成功")


@ZijinBridgeRouter.post("/history/write", summary="批量设置历史数据", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(WRITE_PERMISSION))])
async def history_write_controller(payload: HistoryWriteIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.write_history(payload, token)
    return SuccessResponse(data=data, msg="设置历史数据成功")


@ZijinBridgeRouter.post("/history/export", summary="导出历史数据 CSV/XLSX", dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def history_export_controller(payload: HistoryExportIn, token: ZijinToken = None) -> StreamingResponse:
    query_payload = HistoryQueryIn(**payload.model_dump(exclude={"format"}))
    result = await ZijinBridgeService.history(query_payload, token)
    if payload.format == ExportFormat.XLSX:
        content = ZijinBridgeService.history_xlsx(query_payload, result)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "zijinbridge-history.xlsx"
    else:
        content = ZijinBridgeService.history_csv(query_payload, result)
        media_type = "text/csv; charset=utf-8"
        filename = "zijinbridge-history.csv"
    return StreamingResponse(
        ZijinBridgeService.bytes_stream(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@ZijinBridgeRouter.post("/sql/query", summary="执行紫金桥 SQL 查询", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(SQL_PERMISSION))])
async def sql_query_controller(payload: SqlQueryIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.sql(payload, token)
    return SuccessResponse(data=data, msg="SQL 查询成功")


@ZijinBridgeRouter.post("/alarms/query", summary="查询实时/历史报警", response_model=ResponseSchema[dict[str, Any]], dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def alarm_query_controller(payload: AlarmQueryIn, token: ZijinToken = None) -> JSONResponse:
    data = await ZijinBridgeService.alarms(payload, token)
    return SuccessResponse(data=data, msg="获取报警成功")


@ZijinBridgeRouter.post("/alarms/export", summary="导出报警 CSV/XLSX", dependencies=[Security(AuthPermission(READ_PERMISSION))])
async def alarm_export_controller(payload: AlarmExportIn, token: ZijinToken = None) -> StreamingResponse:
    query_payload = AlarmQueryIn(**payload.model_dump(exclude={"format"}))
    result = await ZijinBridgeService.alarms(query_payload, token)
    if payload.format == ExportFormat.XLSX:
        content = ZijinBridgeService.alarm_xlsx(result)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "zijinbridge-alarms.xlsx"
    else:
        content = ZijinBridgeService.alarm_csv(result)
        media_type = "text/csv; charset=utf-8"
        filename = "zijinbridge-alarms.csv"
    return StreamingResponse(
        ZijinBridgeService.bytes_stream(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
