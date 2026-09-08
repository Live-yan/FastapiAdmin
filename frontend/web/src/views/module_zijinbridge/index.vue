<template>
  <div class="zijin-console">
    <ElCard shadow="never" class="mb-4">
      <div class="flex flex-wrap items-center gap-3">
        <ElInput v-model="baseUrl" class="min-w-[320px] flex-1" placeholder="http://127.0.0.1:8000">
          <template #prepend>紫金桥 REST</template>
        </ElInput>
        <ElTag :type="statusTagType">{{ statusText }}</ElTag>
        <ElButton :loading="checking" @click="checkStatus">检测连接</ElButton>
        <ElButton v-if="!zijinToken" type="primary" @click="loginVisible = true">登录紫金桥</ElButton>
        <ElButton v-else type="warning" plain @click="logout">登出</ElButton>
      </div>
      <ElAlert
        class="mt-3"
        type="info"
        :closable="false"
        show-icon
        title="紫金桥 token 只保存在当前浏览器 sessionStorage；用户名/密码不落库。默认只允许连接本机或内网 REST Service。"
      />
    </ElCard>

    <ElTabs v-model="activeTab" type="border-card">
      <ElTabPane label="点位与实时数据" name="realtime">
        <ElRow :gutter="16">
          <ElCol :xs="24" :lg="8">
            <ElCard shadow="never" class="mb-3">
              <template #header>
                <div class="flex justify-between">
                  <b>对外发布节点</b>
                  <ElButton size="small" :loading="directoryLoading" @click="loadDirectory">刷新</ElButton>
                </div>
              </template>
              <ElTree
                :data="directoryTree"
                node-key="path"
                :props="{ label: 'label', children: 'children' }"
                default-expand-all
                highlight-current
                @node-click="onDirectoryNodeClick"
              />
              <ElEmpty v-if="!directoryTree.length" :image-size="60" description="暂无节点" />
            </ElCard>

            <ElCard shadow="never">
              <template #header>
                <div class="flex justify-between">
                  <b>节点点位</b>
                  <ElButton
                    size="small"
                    type="primary"
                    :loading="pointsLoading"
                    :disabled="!currentNodePath"
                    @click="loadNodePoints"
                  >
                    载入点位
                  </ElButton>
                </div>
              </template>
              <div class="mb-2 text-xs text-gray-500 break-all">{{ currentNodePath || "请选择节点" }}</div>
              <ElTable :data="nodePoints" size="small" max-height="360" @selection-change="onPointSelectionChange">
                <ElTableColumn type="selection" width="42" />
                <ElTableColumn prop="name" label="点位/属性" min-width="160" show-overflow-tooltip />
                <ElTableColumn prop="val" label="当前值" min-width="90" show-overflow-tooltip />
              </ElTable>
              <div class="mt-3 flex gap-2">
                <ElButton
                  size="small"
                  type="success"
                  :disabled="!tableSelectedPoints.length"
                  @click="appendSelectedPoints"
                >
                  加入批量选择
                </ElButton>
                <ElButton size="small" @click="selectedPoints = []">清空已选</ElButton>
              </div>
              <div class="mt-2 text-xs text-gray-500">已选 {{ selectedPoints.length }} 个点位</div>
            </ElCard>
          </ElCol>

          <ElCol :xs="24" :lg="16">
            <ElCard shadow="never">
              <template #header>
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <b>批量实时监视</b>
                  <div class="flex items-center gap-2">
                    <ElSelect v-model="pollSeconds" size="small" style="width: 100px">
                      <ElOption :value="1" label="1 秒" />
                      <ElOption :value="2" label="2 秒" />
                      <ElOption :value="5" label="5 秒" />
                      <ElOption :value="10" label="10 秒" />
                    </ElSelect>
                    <ElSwitch v-model="autoPolling" active-text="自动刷新" @change="onPollingChange" />
                  </div>
                </div>
              </template>
              <ElInput
                v-model="realtimeNamesText"
                type="textarea"
                :rows="4"
                placeholder="A1.PV, A1.DESC, A2.PV；也可从左侧点位批量加入"
              />
              <div class="my-3 flex flex-wrap gap-2">
                <ElButton type="primary" :loading="realtimeLoading" @click="queryRealtime()">查询实时数据</ElButton>
                <ElButton @click="useSharedPoints('realtime')">使用已选点位</ElButton>
                <ElInputNumber v-model="decimal" :min="0" :max="9" controls-position="right" />
                <span class="self-center text-sm text-gray-500">小数位</span>
              </div>
              <ElTable :data="realtimeRows" stripe height="520">
                <ElTableColumn prop="name" label="点位/属性" min-width="200" show-overflow-tooltip />
                <ElTableColumn prop="val" label="值" min-width="160" show-overflow-tooltip />
                <ElTableColumn prop="time" label="时间" min-width="190" />
              </ElTable>
            </ElCard>
          </ElCol>
        </ElRow>
      </ElTabPane>

      <ElTabPane label="历史数据" name="history">
        <ElCard shadow="never">
          <ElForm label-width="110px">
            <ElFormItem label="批量点位">
              <div class="w-full">
                <ElInput
                  v-model="historyNamesText"
                  type="textarea"
                  :rows="4"
                  placeholder="A1.PV, A2.DESC；支持逗号、分号、空格和换行"
                />
                <ElButton class="mt-2" size="small" @click="useSharedPoints('history')">使用已选点位</ElButton>
              </div>
            </ElFormItem>
            <ElFormItem label="查询方式">
              <ElRadioGroup v-model="historyMode">
                <ElRadioButton value="range">时间范围 + 间隔</ElRadioButton>
                <ElRadioButton value="times">指定多个时间点</ElRadioButton>
              </ElRadioGroup>
            </ElFormItem>
            <template v-if="historyMode === 'range'">
              <ElFormItem label="开始/结束">
                <div class="flex flex-wrap gap-2">
                  <ElDatePicker
                    v-model="historyStart"
                    type="datetime"
                    value-format="YYYY-MM-DDTHH:mm:ss.SSS"
                    placeholder="开始时间"
                  />
                  <ElDatePicker
                    v-model="historyEnd"
                    type="datetime"
                    value-format="YYYY-MM-DDTHH:mm:ss.SSS"
                    placeholder="结束时间"
                  />
                </div>
              </ElFormItem>
              <ElFormItem label="采样间隔">
                <ElSelect v-model="historyInterval" style="width: 220px" filterable allow-create>
                  <ElOption :value="250" label="250 ms" />
                  <ElOption :value="1000" label="1 秒" />
                  <ElOption :value="5000" label="5 秒" />
                  <ElOption :value="10000" label="10 秒" />
                  <ElOption :value="60000" label="1 分钟" />
                  <ElOption :value="300000" label="5 分钟" />
                  <ElOption :value="3600000" label="1 小时" />
                </ElSelect>
                <span class="ml-2 text-xs text-gray-500">单位毫秒；后端自动按点位与时间片拆批。</span>
              </ElFormItem>
            </template>
            <ElFormItem v-else label="时间点">
              <ElInput
                v-model="historyTimesText"
                type="textarea"
                :rows="5"
                placeholder="2022-02-22T14:22:33.444&#10;2022-02-22T15:22:34.555"
              />
            </ElFormItem>
            <ElFormItem label="性能参数">
              <div class="flex flex-wrap items-center gap-3">
                <ElSwitch v-model="historyValueOnly" active-text="valueonly" />
                <span class="text-sm text-gray-500">每批点位</span>
                <ElInputNumber v-model="historyNamesBatch" :min="1" :max="500" />
                <span class="text-sm text-gray-500">每批时间点</span>
                <ElInputNumber v-model="historySamplesBatch" :min="1" :max="20000" />
              </div>
            </ElFormItem>
            <ElFormItem>
              <div class="flex flex-wrap gap-2">
                <ElButton type="primary" :loading="historyLoading" @click="queryHistory">查询预览</ElButton>
                <ElButton type="success" :loading="historyExporting" @click="exportHistory('csv')">下载 CSV</ElButton>
                <ElButton type="success" plain :loading="historyExporting" @click="exportHistory('xlsx')">下载 Excel</ElButton>
              </div>
            </ElFormItem>
          </ElForm>
          <ElAlert
            v-if="historyMeta"
            class="mb-3"
            type="success"
            :closable="false"
            :title="`已查询 ${historyMeta.names || 0} 个点位；拆成 ${historyMeta.upstream_requests || 0} 个紫金桥请求；预览最多 1000 行。`"
          />
          <ElTable :data="historyRows" stripe height="500">
            <ElTableColumn prop="name" label="点位/属性" min-width="220" show-overflow-tooltip />
            <ElTableColumn prop="time" label="时间" min-width="210" />
            <ElTableColumn prop="value" label="值" min-width="180" show-overflow-tooltip />
          </ElTable>
        </ElCard>
      </ElTabPane>

      <ElTabPane label="报警中心" name="alarms">
        <ElCard shadow="never">
          <ElForm label-width="100px">
            <ElFormItem label="报警类型">
              <ElRadioGroup v-model="alarmMode">
                <ElRadioButton value="realtime">实时报警</ElRadioButton>
                <ElRadioButton value="history">历史报警</ElRadioButton>
              </ElRadioGroup>
            </ElFormItem>
            <ElFormItem v-if="alarmMode === 'history'" label="时间范围">
              <div class="flex flex-wrap gap-2">
                <ElDatePicker
                  v-model="alarmStart"
                  type="datetime"
                  value-format="YYYY-MM-DDTHH:mm:ss.SSS"
                  placeholder="开始时间"
                />
                <ElDatePicker
                  v-model="alarmEnd"
                  type="datetime"
                  value-format="YYYY-MM-DDTHH:mm:ss.SSS"
                  placeholder="结束时间"
                />
              </div>
            </ElFormItem>
            <ElFormItem label="筛选">
              <div class="flex flex-wrap gap-2">
                <ElInput v-model="alarmTagsText" placeholder="点名 A1,A2,A3" style="width: 220px" />
                <ElInput v-model="alarmOrg" clearable placeholder="目录 org" style="width: 150px" />
                <ElInputNumber v-model="alarmUnit" :min="0" placeholder="单元" style="width: 120px" />
                <ElSelect v-model="alarmLevel" clearable placeholder="最低级别" style="width: 130px">
                  <ElOption :value="0" label="低级及以上" />
                  <ElOption :value="1" label="高级及以上" />
                  <ElOption :value="2" label="紧急" />
                </ElSelect>
                <ElInputNumber v-model="alarmCount" :min="1" :max="100000" />
                <ElSwitch v-model="alarmGroupByTag" active-text="按点名分组" />
              </div>
            </ElFormItem>
            <ElFormItem>
              <div class="flex gap-2">
                <ElButton type="primary" :loading="alarmLoading" @click="queryAlarms">查询报警</ElButton>
                <ElButton type="success" @click="exportAlarms('csv')">下载 CSV</ElButton>
                <ElButton type="success" plain @click="exportAlarms('xlsx')">下载 Excel</ElButton>
              </div>
            </ElFormItem>
          </ElForm>
          <ElTable :data="alarmRows" stripe height="540">
            <ElTableColumn prop="time" label="时间" min-width="180" />
            <ElTableColumn prop="name" label="点名" min-width="110" />
            <ElTableColumn prop="group" label="目录" min-width="150" show-overflow-tooltip />
            <ElTableColumn prop="level" label="级别" width="80">
              <template #default="{ row }">
                <ElTag :type="row.level >= 2 ? 'danger' : row.level === 1 ? 'warning' : 'info'">
                  {{ alarmLevelText(row.level) }}
                </ElTag>
              </template>
            </ElTableColumn>
            <ElTableColumn prop="ack" label="状态" width="90">
              <template #default="{ row }">{{ alarmAckText(row.ack) }}</template>
            </ElTableColumn>
            <ElTableColumn prop="val" label="值" min-width="100" />
            <ElTableColumn prop="limit" label="限值" min-width="100" />
            <ElTableColumn prop="eu" label="单位" width="90" />
            <ElTableColumn prop="desc" label="说明" min-width="160" show-overflow-tooltip />
          </ElTable>
        </ElCard>
      </ElTabPane>

      <ElTabPane label="高级工具" name="advanced">
        <ElRow :gutter="16">
          <ElCol :xs="24" :lg="12">
            <ElCard shadow="never" class="mb-4">
              <template #header><b>注册点名（高频批量取值）</b></template>
              <ElInput v-model="regName" placeholder="注册名，例如 pump_group_01" class="mb-2" />
              <ElInput v-model="regNamesText" type="textarea" :rows="4" placeholder="A1.PV,A2.PV,A3.PV" />
              <div class="mt-2 flex gap-2">
                <ElButton type="primary" @click="registerPoints">注册</ElButton>
                <ElButton @click="queryRegistered">按注册名取值</ElButton>
                <ElButton @click="useSharedPoints('register')">使用已选点位</ElButton>
              </div>
              <pre class="json-box mt-3">{{ registeredOutput }}</pre>
            </ElCard>

            <ElCard shadow="never">
              <template #header><b>批量写实时数据</b></template>
              <ElAlert
                type="warning"
                :closable="false"
                class="mb-2"
                title="写入会直接改变实时数据库点值，请确认点位权限和现场影响。"
              />
              <ElInput v-model="realtimeWriteJson" type="textarea" :rows="9" />
              <ElButton class="mt-2" type="danger" plain @click="writeRealtime">执行写入</ElButton>
            </ElCard>
          </ElCol>

          <ElCol :xs="24" :lg="12">
            <ElCard shadow="never" class="mb-4">
              <template #header><b>SQL 查询控制台</b></template>
              <ElAlert
                type="info"
                :closable="false"
                class="mb-2"
                title="默认只允许无写入副作用的查询语句；写 SQL 还需服务端开启 ZIJINBRIDGE_ALLOW_SQL_WRITE=1。"
              />
              <ElInput v-model="sqlText" type="textarea" :rows="8" />
              <div class="mt-2 flex items-center gap-3">
                <ElSwitch v-model="sqlReadOnly" active-text="只读保护" />
                <ElButton type="primary" :loading="sqlLoading" @click="runSql">执行 SQL</ElButton>
              </div>
              <pre class="json-box mt-3">{{ sqlOutput }}</pre>
            </ElCard>

            <ElCard shadow="never">
              <template #header><b>批量写历史数据</b></template>
              <ElInput v-model="historyWriteJson" type="textarea" :rows="11" />
              <ElButton class="mt-2" type="danger" plain @click="writeHistory">执行写入</ElButton>
            </ElCard>
          </ElCol>
        </ElRow>
      </ElTabPane>
    </ElTabs>

    <ElDialog v-model="loginVisible" title="登录紫金桥 REST 服务" width="460px">
      <ElForm label-width="80px" @submit.prevent="login">
        <ElFormItem label="用户名"><ElInput v-model="loginUser" autocomplete="username" /></ElFormItem>
        <ElFormItem label="密码">
          <ElInput v-model="loginPassword" type="password" show-password autocomplete="current-password" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="loginVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="loginLoading" @click="login">登录</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<script lang="ts" setup>
import dayjs from "dayjs";
import { ElMessage, ElMessageBox } from "element-plus";
import ZijinBridgeAPI, { type AlarmPayload, type HistoryPayload } from "@/api/module_zijinbridge";

defineOptions({ name: "ZijinBridgeConsole" });

type DirectoryNode = { label: string; path: string; desc?: string; children?: DirectoryNode[] };
type PointRow = { name: string; val?: any; time?: string; [key: string]: any };

const BASE_URL_KEY = "zijinbridge.baseUrl";
const TOKEN_KEY = "zijinbridge.token";

const activeTab = ref("realtime");
const baseUrl = ref(sessionStorage.getItem(BASE_URL_KEY) || "http://127.0.0.1:8000");
const zijinToken = ref(sessionStorage.getItem(TOKEN_KEY) || "");
const statusState = ref<"unknown" | "ok" | "auth" | "down">("unknown");
const checking = ref(false);

const statusText = computed(() => {
  if (statusState.value === "ok") return "已连接";
  if (statusState.value === "auth") return "服务可达 · 需要登录";
  if (statusState.value === "down") return "连接失败";
  return "未检测";
});
const statusTagType = computed<"success" | "warning" | "danger" | "info">(() => {
  if (statusState.value === "ok") return "success";
  if (statusState.value === "auth") return "warning";
  if (statusState.value === "down") return "danger";
  return "info";
});
watch(baseUrl, (value) => sessionStorage.setItem(BASE_URL_KEY, value.trim()));

const loginVisible = ref(false);
const loginUser = ref("");
const loginPassword = ref("");
const loginLoading = ref(false);

async function checkStatus() {
  checking.value = true;
  try {
    const res = await ZijinBridgeAPI.status({ base_url: baseUrl.value.trim() }, zijinToken.value);
    const data = res.data?.data || {};
    statusState.value = !data.reachable ? "down" : data.authenticated === false ? "auth" : "ok";
    if (data.reachable) await loadDirectory();
  } catch {
    statusState.value = "down";
  } finally {
    checking.value = false;
  }
}

async function login() {
  if (!loginUser.value || !loginPassword.value) return void ElMessage.warning("请输入用户名和密码");
  loginLoading.value = true;
  try {
    const res = await ZijinBridgeAPI.login({
      base_url: baseUrl.value.trim(),
      user: loginUser.value,
      password: loginPassword.value,
    });
    const token = res.data?.data?.token || "";
    if (!token) throw new Error("登录响应未返回 token");
    zijinToken.value = token;
    sessionStorage.setItem(TOKEN_KEY, token);
    loginPassword.value = "";
    loginVisible.value = false;
    ElMessage.success("紫金桥登录成功");
    await checkStatus();
  } catch (error: any) {
    ElMessage.error(error?.message || "紫金桥登录失败");
  } finally {
    loginLoading.value = false;
  }
}

async function logout() {
  try {
    await ZijinBridgeAPI.logout({ base_url: baseUrl.value.trim() }, zijinToken.value);
  } finally {
    zijinToken.value = "";
    sessionStorage.removeItem(TOKEN_KEY);
    statusState.value = "auth";
    ElMessage.success("已清除紫金桥登录会话");
  }
}

function splitNames(text: string): string[] {
  return Array.from(
    new Set(
      text
        .split(/[\n,，;；\s]+/)
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
}

function normalizeDirectory(items: any[], parent = ""): DirectoryNode[] {
  return (items || []).map((item) => {
    const path = parent ? `${parent}/${item.name}` : item.name;
    return {
      label: item.desc ? `${item.name} · ${item.desc}` : item.name,
      path,
      desc: item.desc,
      children: normalizeDirectory(item.items || [], path),
    };
  });
}

const directoryTree = ref<DirectoryNode[]>([]);
const directoryLoading = ref(false);
const currentNodePath = ref("");
async function loadDirectory() {
  directoryLoading.value = true;
  try {
    const res = await ZijinBridgeAPI.directory({ base_url: baseUrl.value.trim() }, zijinToken.value);
    directoryTree.value = normalizeDirectory(res.data?.data?.items || []);
  } finally {
    directoryLoading.value = false;
  }
}
function onDirectoryNodeClick(node: DirectoryNode) {
  currentNodePath.value = node.path;
}

const decimal = ref(3);
const pointsLoading = ref(false);
const nodePoints = ref<PointRow[]>([]);
const tableSelectedPoints = ref<PointRow[]>([]);
const selectedPoints = ref<string[]>([]);

async function loadNodePoints() {
  if (!currentNodePath.value) return;
  pointsLoading.value = true;
  try {
    const res = await ZijinBridgeAPI.points(
      {
        base_url: baseUrl.value.trim(),
        node_path: currentNodePath.value,
        recursion: true,
        decimal: decimal.value,
      },
      zijinToken.value
    );
    nodePoints.value = (res.data?.data?.items || []).map((item: any) => ({
      ...item,
      name: item.name || item.tag || "",
      val: item.val ?? item.PV ?? "",
    }));
  } finally {
    pointsLoading.value = false;
  }
}
function onPointSelectionChange(rows: PointRow[]) {
  tableSelectedPoints.value = rows;
}
function appendSelectedPoints() {
  selectedPoints.value = Array.from(
    new Set([...selectedPoints.value, ...tableSelectedPoints.value.map((row) => row.name).filter(Boolean)])
  );
  ElMessage.success(`已选择 ${selectedPoints.value.length} 个点位`);
}

const realtimeNamesText = ref("");
const realtimeRows = ref<PointRow[]>([]);
const realtimeLoading = ref(false);
const autoPolling = ref(false);
const pollSeconds = ref(2);
let pollingTimer: ReturnType<typeof setInterval> | null = null;

async function queryRealtime(silent = false) {
  const names = splitNames(realtimeNamesText.value);
  if (!names.length) {
    if (!silent) ElMessage.warning("请先选择或输入实时点位");
    return;
  }
  realtimeLoading.value = !silent;
  try {
    const res = await ZijinBridgeAPI.realtime(
      { base_url: baseUrl.value.trim(), names, decimal: decimal.value, value_only: false },
      zijinToken.value
    );
    const items = res.data?.data?.items || [];
    realtimeRows.value = items.map((item: any) => ({
      name: item.name || item.tag || "",
      val: item.val ?? item.PV ?? item.value ?? "",
      time: item.PVTIME || item.time || "",
    }));
  } finally {
    realtimeLoading.value = false;
  }
}
function stopPolling() {
  if (pollingTimer) clearInterval(pollingTimer);
  pollingTimer = null;
}
function onPollingChange(enabled: boolean) {
  stopPolling();
  if (enabled) {
    void queryRealtime(true);
    pollingTimer = setInterval(() => void queryRealtime(true), pollSeconds.value * 1000);
  }
}
watch(pollSeconds, () => {
  if (autoPolling.value) onPollingChange(true);
});
onBeforeUnmount(stopPolling);

const historyNamesText = ref("");
const historyMode = ref<"range" | "times">("range");
const historyStart = ref(dayjs().subtract(1, "hour").format("YYYY-MM-DDTHH:mm:ss.SSS"));
const historyEnd = ref(dayjs().format("YYYY-MM-DDTHH:mm:ss.SSS"));
const historyInterval = ref<number | string>(1000);
const historyTimesText = ref("");
const historyValueOnly = ref(false);
const historyNamesBatch = ref(50);
const historySamplesBatch = ref(5000);
const historyRows = ref<Array<{ name: string; time: string; value: any }>>([]);
const historyMeta = ref<any>(null);
const historyLoading = ref(false);
const historyExporting = ref(false);

function makeHistoryPayload(): HistoryPayload {
  const names = splitNames(historyNamesText.value);
  if (!names.length) throw new Error("请至少选择一个历史点位");
  const common = {
    base_url: baseUrl.value.trim(),
    mode: historyMode.value,
    names,
    decimal: decimal.value,
    value_only: historyValueOnly.value,
    names_per_request: historyNamesBatch.value,
    samples_per_request: historySamplesBatch.value,
  } satisfies HistoryPayload;
  if (historyMode.value === "times") {
    const times = splitNames(historyTimesText.value);
    if (!times.length) throw new Error("请输入至少一个时间点");
    return { ...common, times };
  }
  if (!historyStart.value || !historyEnd.value) throw new Error("请选择开始和结束时间");
  return {
    ...common,
    start_time: historyStart.value,
    end_time: historyEnd.value,
    interval: Number(historyInterval.value),
  };
}

function toHistoryPreview(payload: HistoryPayload, result: any) {
  const rows: Array<{ name: string; time: string; value: any }> = [];
  for (const item of result.items || []) {
    (item.vals || []).forEach((value: any, index: number) => {
      let time = "";
      let val = value;
      if (value && typeof value === "object" && !Array.isArray(value)) {
        time = value.time || "";
        val = value.val;
      } else if (payload.mode === "times") {
        time = payload.times?.[index] || "";
      } else if (payload.start_time && payload.interval) {
        time = dayjs(payload.start_time)
          .add(payload.interval * index, "millisecond")
          .format("YYYY-MM-DDTHH:mm:ss.SSS");
      }
      if (rows.length < 1000) rows.push({ name: item.name, time, value: val });
    });
  }
  return rows;
}

async function queryHistory() {
  historyLoading.value = true;
  try {
    const payload = makeHistoryPayload();
    const res = await ZijinBridgeAPI.history(payload, zijinToken.value);
    const result = res.data?.data || {};
    historyRows.value = toHistoryPreview(payload, result);
    historyMeta.value = result.meta || { names: payload.names.length };
  } catch (error: any) {
    ElMessage.error(error?.message || "历史数据查询失败");
  } finally {
    historyLoading.value = false;
  }
}
async function exportHistory(format: "csv" | "xlsx") {
  historyExporting.value = true;
  try {
    await ZijinBridgeAPI.exportHistory(makeHistoryPayload(), zijinToken.value, format);
    ElMessage.success(`历史数据 ${format.toUpperCase()} 已下载`);
  } catch (error: any) {
    ElMessage.error(error?.message || "历史数据导出失败");
  } finally {
    historyExporting.value = false;
  }
}

const alarmMode = ref<"realtime" | "history">("realtime");
const alarmStart = ref(dayjs().subtract(1, "day").format("YYYY-MM-DDTHH:mm:ss.SSS"));
const alarmEnd = ref(dayjs().format("YYYY-MM-DDTHH:mm:ss.SSS"));
const alarmTagsText = ref("");
const alarmOrg = ref("");
const alarmUnit = ref<number | undefined>();
const alarmLevel = ref<number | undefined>();
const alarmCount = ref(1000);
const alarmGroupByTag = ref(false);
const alarmRows = ref<any[]>([]);
const alarmLoading = ref(false);

function makeAlarmPayload(): AlarmPayload {
  const payload: AlarmPayload = {
    base_url: baseUrl.value.trim(),
    realalmcount: alarmCount.value,
    tags: splitNames(alarmTagsText.value),
    org: alarmOrg.value || undefined,
    unit: alarmUnit.value,
    level: alarmLevel.value,
    group_by_tag: alarmGroupByTag.value,
  };
  if (alarmMode.value === "history") {
    payload.start_time = alarmStart.value;
    payload.end_time = alarmEnd.value;
  }
  return payload;
}
async function queryAlarms() {
  alarmLoading.value = true;
  try {
    const res = await ZijinBridgeAPI.alarms(makeAlarmPayload(), zijinToken.value);
    alarmRows.value = res.data?.data?.items || [];
  } finally {
    alarmLoading.value = false;
  }
}
async function exportAlarms(format: "csv" | "xlsx") {
  await ZijinBridgeAPI.exportAlarms(makeAlarmPayload(), zijinToken.value, format);
  ElMessage.success(`报警数据 ${format.toUpperCase()} 已下载`);
}
function alarmLevelText(level: number) {
  return level === 2 ? "紧急" : level === 1 ? "高级" : "低级";
}
function alarmAckText(ack: number) {
  return ({ 0: "未确认", 1: "已确认", 2: "已恢复", 3: "已禁止" } as Record<number, string>)[ack] ?? String(ack);
}

const regName = ref("fast_group_01");
const regNamesText = ref("");
const registeredOutput = ref("");
async function registerPoints() {
  const names = splitNames(regNamesText.value);
  if (!names.length) return void ElMessage.warning("请输入或选择注册点位");
  if (!zijinToken.value) return void ElMessage.warning("注册点名必须先登录紫金桥");
  await ZijinBridgeAPI.register({ base_url: baseUrl.value.trim(), regname: regName.value, names }, zijinToken.value);
}
async function queryRegistered() {
  if (!zijinToken.value) return void ElMessage.warning("注册项取值必须先登录紫金桥");
  const res = await ZijinBridgeAPI.registered(
    { base_url: baseUrl.value.trim(), regname: regName.value, decimal: decimal.value },
    zijinToken.value
  );
  registeredOutput.value = JSON.stringify(res.data?.data || {}, null, 2);
}

const realtimeWriteJson = ref(`[
  {"name": "A1.PV", "val": 40},
  {"name": "A2.PV", "val": 60}
]`);
async function writeRealtime() {
  try {
    const items = JSON.parse(realtimeWriteJson.value);
    if (!Array.isArray(items) || !items.length) throw new Error("JSON 必须是非空数组");
    await ElMessageBox.confirm("这会直接写入紫金桥实时数据，确认继续？", "危险操作", { type: "warning" });
    await ZijinBridgeAPI.writeRealtime({ base_url: baseUrl.value.trim(), items }, zijinToken.value);
  } catch (error: any) {
    if (error === "cancel" || error === "close") return;
    ElMessage.error(error?.message || "实时数据写入失败");
  }
}

const historyWriteJson = ref(`[
  {
    "name": "A1.PV",
    "vals": [
      {"time": "2022-02-22T15:22:34.555", "val": 50},
      {"time": "2022-02-22T15:22:35.555", "val": 51}
    ]
  }
]`);
async function writeHistory() {
  try {
    const items = JSON.parse(historyWriteJson.value);
    if (!Array.isArray(items) || !items.length) throw new Error("JSON 必须是非空数组");
    await ElMessageBox.confirm("这会写入紫金桥历史数据，确认继续？", "危险操作", { type: "warning" });
    await ZijinBridgeAPI.writeHistory({ base_url: baseUrl.value.trim(), items }, zijinToken.value);
  } catch (error: any) {
    if (error === "cancel" || error === "close") return;
    ElMessage.error(error?.message || "历史数据写入失败");
  }
}

const sqlText = ref("select name, pv, euhi from realdata where kind<250");
const sqlReadOnly = ref(true);
const sqlLoading = ref(false);
const sqlOutput = ref("");
async function runSql() {
  sqlLoading.value = true;
  try {
    const res = await ZijinBridgeAPI.sql(
      { base_url: baseUrl.value.trim(), query: sqlText.value, read_only: sqlReadOnly.value },
      zijinToken.value
    );
    sqlOutput.value = JSON.stringify(res.data?.data || {}, null, 2);
  } finally {
    sqlLoading.value = false;
  }
}

function useSharedPoints(target: "realtime" | "history" | "register") {
  const text = selectedPoints.value.join(", ");
  if (target === "realtime") realtimeNamesText.value = text;
  if (target === "history") historyNamesText.value = text;
  if (target === "register") regNamesText.value = text;
}

onMounted(() => {
  if (baseUrl.value) void checkStatus();
});
</script>

<style scoped>
.json-box {
  max-height: 300px;
  overflow: auto;
  padding: 12px;
  margin-bottom: 0;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
}
</style>
