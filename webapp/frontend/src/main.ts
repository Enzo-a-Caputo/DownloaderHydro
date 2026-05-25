import { createMap, WatershedLayers, InventoryLayer } from "./map";
import { api, UnauthorizedError, type Station } from "./api";

const mapEl       = document.getElementById("map")!;
const statusEl    = document.getElementById("status")!;
const wsInfo      = document.querySelector<HTMLElement>("#watershed-info")!;
const stSection   = document.querySelector<HTMLElement>("#stations-section")!;
const precisionEl = document.getElementById("precision") as HTMLSelectElement;
const snapSensEl  = document.getElementById("snap-sensitivity") as HTMLSelectElement;

// Filtros do inventário (painel dropdown)
const filterPluEl   = document.getElementById("filter-plu")   as HTMLInputElement;
const filterFluEl   = document.getElementById("filter-flu")   as HTMLInputElement;
const filterAtivaEl = document.getElementById("filter-ativa") as HTMLInputElement;
const filterBtn     = document.getElementById("filter-btn")   as HTMLButtonElement;
const filterPanel   = document.getElementById("filter-panel") as HTMLElement;

// ── Auth ──────────────────────────────────────────────────────────────────────
const loginOverlay = document.getElementById("login-overlay")!;
const loginForm    = document.getElementById("login-form") as HTMLFormElement;
const loginIdEl    = document.getElementById("login-id") as HTMLInputElement;
const loginPwEl    = document.getElementById("login-pw") as HTMLInputElement;
const loginErrEl   = document.getElementById("login-error") as HTMLParagraphElement;
const loginBtn     = document.getElementById("login-btn") as HTMLButtonElement;
const authInfoEl   = document.getElementById("auth-info")!;
const authUserEl   = document.getElementById("auth-user")!;
const logoutBtn    = document.getElementById("logout-btn") as HTMLButtonElement;

function showLogin() {
  loginOverlay.classList.remove("hidden");
}
function hideLogin(identificador: string) {
  loginOverlay.classList.add("hidden");
  authInfoEl.hidden = false;
  authUserEl.textContent = `ANA: ${identificador}`;
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  loginErrEl.hidden = true;
  loginBtn.disabled = true;
  loginBtn.textContent = "Entrando…";
  try {
    const res = await api.login(loginIdEl.value.trim(), loginPwEl.value);
    hideLogin(res.identificador ?? loginIdEl.value.trim());
    statusEl.textContent = "Clique no mapa para delinear uma bacia.";
  } catch (err) {
    loginErrEl.textContent = err instanceof Error ? err.message : "Erro ao autenticar.";
    loginErrEl.hidden = false;
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = "Entrar";
  }
});

logoutBtn.addEventListener("click", async () => {
  await api.logout();
  authInfoEl.hidden = true;
  authUserEl.textContent = "";
  showLogin();
});

// Verifica sessão existente ao abrir o app
(async () => {
  try {
    const me = await api.authMe();
    hideLogin(me.identificador ?? "");
    statusEl.textContent = "Clique no mapa para delinear uma bacia.";
  } catch {
    showLogin();
  }
})();

const map      = createMap(mapEl);
const layers   = new WatershedLayers(map);
const inventory = new InventoryLayer(map);

// ── Estado do sidebar (módulo — sobrevive a re-renders dos filtros) ───────────
let _allPluv: Station[] = [];
let _allFluv: Station[] = [];
let _sbShowPlu  = true;
let _sbShowFlu  = true;
let _sbSoAtivas = false;

function renderSidebar() {
  if (_allPluv.length === 0 && _allFluv.length === 0) return;

  const all   = [..._allPluv, ..._allFluv];
  const total = all.length;

  // Lê estado atual dos filtros do header (idêntico ao que vai para o mapa)
  const mapWantPlu = filterPluEl?.checked ?? true;
  const mapWantFlu = filterFluEl?.checked ?? true;
  const mapDtypes  = new Set<string>();
  document.querySelectorAll<HTMLInputElement>(".filter-dtype:checked").forEach(cb => {
    if (cb.dataset.col) mapDtypes.add(cb.dataset.col);
  });
  const mapAtivas = filterAtivaEl?.checked ?? false;

  const filtered = all.filter(s => {
    const isPlu = s.tipo.includes("Pluvi");
    const isFlu = s.tipo.includes("Fluvi");
    // filtro do mapa (mesma lógica do InventoryLayer)
    const mapTipoOk  = (!mapWantPlu && !mapWantFlu)
      || (mapWantPlu && isPlu) || (mapWantFlu && isFlu);
    const mapAtivaOk = !mapAtivas || String(s.props["Operando"]) === "1";
    const mapDtypeOk = mapDtypes.size === 0
      || [...mapDtypes].every(col => String(s.props[col] ?? "0") === "1");
    if (!mapTipoOk || !mapAtivaOk || !mapDtypeOk) return false;
    // filtro secundário do sidebar
    const sbTipoOk  = (_sbShowPlu && isPlu) || (_sbShowFlu && isFlu);
    const sbAtivaOk = !_sbSoAtivas || String(s.props["Operando"]) === "1";
    return sbTipoOk && sbAtivaOk;
  });

  stSection.innerHTML = `
    <h2>Estações na bacia (${filtered.length}/${total})</h2>
    <div class="station-filters">
      <label><input type="checkbox" id="sb-plu" ${_sbShowPlu ? "checked" : ""}> <span class="dot plu"></span> Pluviométricas (${_allPluv.length})</label>
      <label><input type="checkbox" id="sb-flu" ${_sbShowFlu ? "checked" : ""}> <span class="dot flu"></span> Fluviométricas (${_allFluv.length})</label>
      <label><input type="checkbox" id="sb-ativa" ${_sbSoAtivas ? "checked" : ""}> Só em operação</label>
    </div>
    <div class="station-list">
      ${filtered.map(stationCard).join("")}
    </div>
  `;

  document.getElementById("sb-plu")?.addEventListener("change", e => {
    _sbShowPlu = (e.target as HTMLInputElement).checked; renderSidebar();
  });
  document.getElementById("sb-flu")?.addEventListener("change", e => {
    _sbShowFlu = (e.target as HTMLInputElement).checked; renderSidebar();
  });
  document.getElementById("sb-ativa")?.addEventListener("change", e => {
    _sbSoAtivas = (e.target as HTMLInputElement).checked; renderSidebar();
  });

  stSection.querySelectorAll<HTMLButtonElement>(".download-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openDownloadMenu(btn, btn.dataset.codigo!);
    });
  });

  stSection.querySelectorAll(".station-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      const details = btn.closest(".station-card")?.querySelector(".station-details");
      if (details) {
        const open = (details as HTMLElement).style.display !== "none";
        (details as HTMLElement).style.display = open ? "none" : "block";
        btn.textContent = open ? "▶ detalhes" : "▼ detalhes";
      }
    });
  });
}

// ── Filtros do mapa ───────────────────────────────────────────────────────────
function applyInventoryFilter() {
  const tipos = new Set<string>();
  if (filterPluEl?.checked) tipos.add("Pluviométrica");
  if (filterFluEl?.checked) tipos.add("Fluviométrica");
  const dtypes = new Set<string>();
  document.querySelectorAll<HTMLInputElement>(".filter-dtype:checked").forEach(cb => {
    if (cb.dataset.col) dtypes.add(cb.dataset.col);
  });
  inventory.applyFilter(tipos, dtypes, filterAtivaEl?.checked ?? false);
  renderSidebar();
}

filterPluEl?.addEventListener("change", applyInventoryFilter);
filterFluEl?.addEventListener("change", applyInventoryFilter);
filterAtivaEl?.addEventListener("change", applyInventoryFilter);
document.querySelectorAll<HTMLInputElement>(".filter-dtype").forEach(cb => {
  cb.addEventListener("change", applyInventoryFilter);
});

// toggle do painel
filterBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const opening = filterPanel.hidden;
  filterPanel.hidden = !opening;
  filterBtn.textContent = opening ? "Filtros ▴" : "Filtros ▾";
});
filterPanel.addEventListener("click", (e) => e.stopPropagation());
document.addEventListener("click", () => {
  if (!filterPanel.hidden) {
    filterPanel.hidden = true;
    filterBtn.textContent = "Filtros ▾";
  }
});

// ── Menu de download (global, reposicionado por estação) ──────────────────────
const DOWNLOAD_KINDS = [
  { id: "chuva",                 label: "Chuva" },
  { id: "cota",                  label: "Cota" },
  { id: "vazao",                 label: "Vazão" },
  { id: "curva_descarga",        label: "Curva de Descarga" },
  { id: "perfil_transversal",    label: "Perfil Transversal" },
  { id: "qa",                    label: "Qualidade da Água" },
  { id: "resumo_descarga",       label: "Resumo de Descarga" },
  { id: "sedimentos",            label: "Sedimentos" },
  { id: "granulometria",         label: "Granulometria" },
  { id: "telemetrica_detalhada", label: "Telemétrica (detalhada)" },
  { id: "telemetrica_adotada",   label: "Telemétrica (adotada)" },
];

// Colunas Tipo_Estacao_* que habilitam cada kind (OR entre colunas da lista)
const KIND_COLS: Record<string, string[]> = {
  chuva:                 ["Tipo_Estacao_Pluviometro", "Tipo_Estacao_Registrador_Chuva"],
  cota:                  ["Tipo_Estacao_Registrador_Nivel", "Tipo_Estacao_Escala"],
  vazao:                 ["Tipo_Estacao_Desc_Liquida"],
  curva_descarga:        ["Tipo_Estacao_Desc_Liquida"],
  perfil_transversal:    ["Tipo_Estacao_Desc_Liquida"],
  qa:                    ["Tipo_Estacao_Qual_Agua"],
  resumo_descarga:       ["Tipo_Estacao_Desc_Liquida"],
  sedimentos:            ["Tipo_Estacao_Sedimentos"],
  granulometria:         ["Tipo_Estacao_Sedimentos"],
  telemetrica_detalhada: ["Tipo_Estacao_Telemetrica"],
  telemetrica_adotada:   ["Tipo_Estacao_Telemetrica"],
};

// Props das estações carregadas, indexadas por código — para filtrar o menu
const stationPropsMap = new Map<string, Record<string, unknown>>();

const dlMenu = document.createElement("div");
dlMenu.className = "download-menu";
dlMenu.hidden = true;
document.body.appendChild(dlMenu);

let dlActiveBtn: HTMLButtonElement | null = null;
let dlActiveCodigo = "";

function openDownloadMenu(triggerBtn: HTMLButtonElement, codigo: string) {
  dlActiveBtn = triggerBtn;
  dlActiveCodigo = codigo;

  const props = stationPropsMap.get(codigo) ?? {};
  const validKinds = DOWNLOAD_KINDS.filter(k => {
    const cols = KIND_COLS[k.id];
    if (!cols || cols.length === 0) return true;
    return cols.some(col => String(props[col] ?? "0") === "1");
  });

  dlMenu.innerHTML = validKinds.length > 0
    ? validKinds.map(k => `<button class="dl-kind-btn" data-kind="${k.id}">${k.label}</button>`).join("")
    : `<span class="dl-empty">Nenhuma série no inventário</span>`;

  const rect = triggerBtn.getBoundingClientRect();
  dlMenu.style.left = `${Math.min(rect.left, window.innerWidth - 210)}px`;
  dlMenu.style.top  = `${rect.bottom + 4}px`;
  dlMenu.hidden = false;
}

document.addEventListener("click", () => { dlMenu.hidden = true; });

dlMenu.addEventListener("click", async (e) => {
  e.stopPropagation();
  const btn = (e.target as HTMLElement).closest(".dl-kind-btn") as HTMLButtonElement | null;
  if (!btn) return;
  const kind = btn.dataset.kind!;
  dlMenu.hidden = true;
  const trigBtn = dlActiveBtn;
  if (trigBtn) trigBtn.disabled = true;
  try {
    const { job_id } = await api.enqueueDownload({
      codigo_estacao: dlActiveCodigo,
      kind,
      ano_inicial: 1900,
      ano_final: 2025,
    });
    statusEl.textContent = `Job enfileirado (${kind}): ${job_id}`;
  } catch (err) {
    if (err instanceof UnauthorizedError) { showLogin(); return; }
    statusEl.textContent = `Falha: ${(err as Error).message}`;
    if (trigBtn) trigBtn.disabled = false;
  }
});

function stationsToGeoJSON(pluv: Station[], fluv: Station[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: [...pluv, ...fluv].map(s => ({
      type: "Feature" as const,
      properties: s.props,
      geometry: { type: "Point" as const, coordinates: [s.lng, s.lat] },
    })),
  };
}

// ── Click no mapa → delineação ────────────────────────────────────────────────
map.on("click", async (e) => {
  const { lat, lng } = e.latlng;
  const precision = precisionEl.value as "auto" | "high" | "low";
  const snapSens  = snapSensEl.value as "auto" | "medium" | "small" | "micro";
  statusEl.textContent = `Delineando (${lat.toFixed(4)}, ${lng.toFixed(4)}) [${precision} · ${snapSensEl.options[snapSensEl.selectedIndex].text}]…`;

  try {
    const result = await api.delineate(lat, lng, precision, snapSens);
    layers.show({
      watershed: result.watershed,
      rivers: result.rivers,
      outlet: [lat, lng],
      snap: [result.lat_snap, result.lng_snap],
    });

    wsInfo.innerHTML = `
      <h2>Bacia</h2>
      <p><b>Área:</b> ${result.area_km2.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} km²</p>
      <p><b>Megabacia Pfaf-2:</b> ${result.basin_pfaf2}</p>
      <p><b>Modo:</b> ${result.mode}</p>
      <p><b>Distância de snap:</b> ${result.snap_dist_m.toFixed(1)} m</p>
    `;

    statusEl.textContent = "Buscando estações na bacia…";
    try {
      const stations = await api.stations(result.watershed);
      inventory.load(stationsToGeoJSON(stations.pluviometricas, stations.fluviometricas));
      renderStations(stations.pluviometricas, stations.fluviometricas);
      applyInventoryFilter();
      const total = stations.pluviometricas.length + stations.fluviometricas.length;
      statusEl.textContent = `${total} estações na bacia (${stations.pluviometricas.length} pluv · ${stations.fluviometricas.length} fluv). Clique para redelinear.`;
    } catch (err) {
      stSection.innerHTML = `<h2>Estações na bacia</h2><p class="muted">${(err as Error).message}</p>`;
      statusEl.textContent = "Bacia delineada. Inventário ANA não disponível.";
    }
  } catch (err) {
    if (err instanceof UnauthorizedError) { showLogin(); return; }
    statusEl.textContent = `Erro: ${(err as Error).message}`;
  }
});


// ── Sidebar: estações na bacia ────────────────────────────────────────────────
function renderStations(pluv: Station[], fluv: Station[]) {
  stationPropsMap.clear();
  [...pluv, ...fluv].forEach(s => stationPropsMap.set(s.codigo, s.props));
  _allPluv    = pluv;
  _allFluv    = fluv;
  _sbShowPlu  = true;
  _sbShowFlu  = true;
  _sbSoAtivas = false;
  renderSidebar();
}

function stationCard(s: Station): string {
  const isPlu  = s.tipo.includes("Pluvi");
  const ativa  = String(s.props["Operando"]) === "1";
  const bacia  = String(s.props["Bacia_Nome"] ?? "");
  const municipio = String(s.props["Municipio_Nome"] ?? "");
  const resp   = String(s.props["Responsavel_Sigla"] ?? "");

  const detailRows = Object.entries(s.props)
    .filter(([k, v]) => !["lat","lng","geometry"].includes(k) && v !== null && v !== "" && v !== "None" && v !== "null")
    .map(([k, v]) => `<tr><td class="pk">${k}</td><td>${v}</td></tr>`)
    .join("");

  return `
    <div class="station-card ${isPlu ? "plu" : "flu"}">
      <div class="station-header">
        <span class="dot ${isPlu ? "plu" : "flu"}"></span>
        <b>${s.codigo}</b>
        <span class="station-name">${s.nome ?? ""}</span>
        ${ativa ? '<span class="badge-ativa">em operação</span>' : ""}
      </div>
      <div class="station-meta">
        <span>${municipio}</span> · <span>${bacia}</span> · <span>${resp}</span>
      </div>
      <div class="station-actions">
        <button class="station-toggle">▶ detalhes</button>
        <button class="download-btn" data-codigo="${s.codigo}">↓ baixar ▾</button>
      </div>
      <div class="station-details" style="display:none">
        <table class="props-table">${detailRows}</table>
      </div>
    </div>
  `;
}
