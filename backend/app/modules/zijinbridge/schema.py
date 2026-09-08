from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class HistoryMode(StrEnum):
    """历史数据查询模式。"""

    TIMES = "times"
    RANGE = "range"


class ZijinConnection(BaseModel):
    """紫金桥 REST 服务连接参数。"""

    base_url: str = Field(default="http://127.0.0.1:8000", description="紫金桥 REST Service 地址")


class LoginIn(ZijinConnection):
    user: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LogoutIn(ZijinConnection):
    pass


class RealDataQueryIn(ZijinConnection):
    names: list[str] | None = Field(default=None, description="点名+属性，例如 A1.PV")
    tags: list[str] | None = Field(default=None, description="不带属性的点名，例如 A1")
    pars: list[str] | None = Field(default=None, description="属性，例如 PV/PVTIME/DESC")
    decimal: int | None = Field(default=None, ge=0, le=9)
    value_only: bool = False

    @model_validator(mode="after")
    def validate_query(self) -> "RealDataQueryIn":
        if self.names:
            return self
        if self.tags and self.pars:
            return self
        raise ValueError("names 或 tags+pars 至少提供一种查询方式")


class RegisterPointsIn(ZijinConnection):
    regname: str = Field(min_length=1, max_length=128)
    names: list[str] = Field(min_length=1, max_length=5000)


class RegisteredQueryIn(ZijinConnection):
    regname: str = Field(min_length=1, max_length=128)
    decimal: int | None = Field(default=None, ge=0, le=9)


class RealDataWriteItem(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    val: Any


class RealDataWriteIn(ZijinConnection):
    items: list[RealDataWriteItem] = Field(min_length=1, max_length=10000)


class HistoryQueryIn(ZijinConnection):
    mode: HistoryMode = HistoryMode.RANGE
    names: list[str] = Field(min_length=1, max_length=5000)
    times: list[str] = Field(default_factory=list, max_length=50000)
    start_time: str | None = None
    end_time: str | None = None
    interval: int | None = Field(default=1000, ge=1, le=86_400_000, description="毫秒")
    decimal: int | None = Field(default=None, ge=0, le=9)
    value_only: bool = False
    names_per_request: int = Field(default=50, ge=1, le=500)
    samples_per_request: int = Field(default=5000, ge=1, le=20000)

    @model_validator(mode="after")
    def validate_history_query(self) -> "HistoryQueryIn":
        if self.mode == HistoryMode.TIMES:
            if not self.times:
                raise ValueError("times 模式必须提供至少一个时间点")
        else:
            if not self.start_time or not self.end_time or not self.interval:
                raise ValueError("range 模式必须提供 start_time、end_time、interval")
        return self


class HistoryWriteValue(BaseModel):
    time: str
    val: Any


class HistoryWriteItem(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    vals: list[HistoryWriteValue] = Field(min_length=1, max_length=50000)


class HistoryWriteIn(ZijinConnection):
    items: list[HistoryWriteItem] = Field(min_length=1, max_length=5000)


class SqlQueryIn(ZijinConnection):
    query: str = Field(min_length=1, max_length=100_000)
    read_only: bool = True


class AlarmQueryIn(ZijinConnection):
    realalmcount: int | None = Field(default=None, ge=1, le=100000)
    org: str | None = None
    unit: int | None = None
    level: int | None = Field(default=None, ge=0)
    tags: list[str] | None = None
    group_by_tag: bool = False
    start_time: str | None = None
    end_time: str | None = None

    @model_validator(mode="after")
    def validate_alarm_time(self) -> "AlarmQueryIn":
        if bool(self.start_time) != bool(self.end_time):
            raise ValueError("历史报警查询必须同时提供 start_time 和 end_time")
        return self


class ExportFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"


class HistoryExportIn(HistoryQueryIn):
    format: ExportFormat = ExportFormat.CSV


class AlarmExportIn(AlarmQueryIn):
    format: ExportFormat = ExportFormat.CSV


class NodePointsQueryIn(ZijinConnection):
    node_path: str = Field(min_length=1, max_length=1000)
    recursion: bool = True
    decimal: int | None = Field(default=None, ge=0, le=9)


class ServiceStatusOut(BaseModel):
    base_url: str
    reachable: bool
    authenticated: bool | None = None
    upstream_code: int | None = None
    message: str = ""
