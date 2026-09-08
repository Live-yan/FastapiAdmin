import { saveAs } from "file-saver";
import { request } from "@utils";

const API_PATH = "/industrial/zijinbridge";

export interface ConnectionConfig {
  base_url: string;
}

export interface HistoryPayload extends ConnectionConfig {
  mode: "times" | "range";
  names: string[];
  times?: string[];
  start_time?: string;
  end_time?: string;
  interval?: number;
  decimal?: number;
  value_only?: boolean;
  names_per_request?: number;
  samples_per_request?: number;
  format?: "csv" | "xlsx";
}

export interface AlarmPayload extends ConnectionConfig {
  realalmcount?: number;
  org?: string;
  unit?: number;
  level?: number;
  tags?: string[];
  group_by_tag?: boolean;
  start_time?: string;
  end_time?: string;
  format?: "csv" | "xlsx";
}

function zijinHeaders(token?: string) {
  return token ? { "X-Zijin-Token": token } : {};
}

async function exportBlob(
  path: string,
  payload: Record<string, any>,
  token: string,
  filename: string
) {
  const response = await request.post<Blob>(`${API_PATH}${path}`, payload, {
    responseType: "blob",
    headers: zijinHeaders(token),
  });
  const disposition = response.headers["content-disposition"] || "";
  const matched = disposition.match(/filename="?([^";]+)"?/i);
  saveAs(response.data, matched?.[1] || filename);
}

const ZijinBridgeAPI = {
  login(payload: ConnectionConfig & { user: string; password: string }) {
    return request<ApiResponse>({
      url: `${API_PATH}/login`,
      method: "post",
      data: payload,
      showSuccessMessage: false,
    });
  },

  logout(payload: ConnectionConfig, token: string) {
    return request<ApiResponse>({
      url: `${API_PATH}/logout`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  status(payload: ConnectionConfig, token = "") {
    return request<ApiResponse>({
      url: `${API_PATH}/status`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  directory(payload: ConnectionConfig, token = "", nodePath = "") {
    return request<ApiResponse>({
      url: `${API_PATH}/directory`,
      method: "post",
      params: { node_path: nodePath },
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  points(
    payload: ConnectionConfig & { node_path: string; recursion?: boolean; decimal?: number },
    token = ""
  ) {
    return request<ApiResponse>({
      url: `${API_PATH}/points`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  realtime(
    payload: ConnectionConfig & {
      names?: string[];
      tags?: string[];
      pars?: string[];
      decimal?: number;
      value_only?: boolean;
    },
    token = ""
  ) {
    return request<ApiResponse>({
      url: `${API_PATH}/realtime/query`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  register(
    payload: ConnectionConfig & { regname: string; names: string[] },
    token: string
  ) {
    return request<ApiResponse>({
      url: `${API_PATH}/realtime/register`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
    });
  },

  registered(
    payload: ConnectionConfig & { regname: string; decimal?: number },
    token: string
  ) {
    return request<ApiResponse>({
      url: `${API_PATH}/realtime/registered`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  writeRealtime(
    payload: ConnectionConfig & { items: Array<{ name: string; val: any }> },
    token = ""
  ) {
    return request<ApiResponse>({
      url: `${API_PATH}/realtime/write`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
    });
  },

  history(payload: HistoryPayload, token = "") {
    return request<ApiResponse>({
      url: `${API_PATH}/history/query`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  writeHistory(payload: ConnectionConfig & { items: any[] }, token = "") {
    return request<ApiResponse>({
      url: `${API_PATH}/history/write`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
    });
  },

  exportHistory(payload: HistoryPayload, token = "", format: "csv" | "xlsx" = "csv") {
    return exportBlob(
      "/history/export",
      { ...payload, format },
      token,
      `zijinbridge-history.${format}`
    );
  },

  sql(payload: ConnectionConfig & { query: string; read_only?: boolean }, token = "") {
    return request<ApiResponse>({
      url: `${API_PATH}/sql/query`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  alarms(payload: AlarmPayload, token = "") {
    return request<ApiResponse>({
      url: `${API_PATH}/alarms/query`,
      method: "post",
      data: payload,
      headers: zijinHeaders(token),
      showSuccessMessage: false,
    });
  },

  exportAlarms(payload: AlarmPayload, token = "", format: "csv" | "xlsx" = "csv") {
    return exportBlob(
      "/alarms/export",
      { ...payload, format },
      token,
      `zijinbridge-alarms.${format}`
    );
  },
};

export default ZijinBridgeAPI;
