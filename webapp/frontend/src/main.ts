import { createMap, WatershedLayers } from "./map";
import { api, type Station } from "./api";

const mapEl = document.getElementById("map")!;
const statusEl = document.getElementById("status")!;
const wsInfo = document.querySelector<HTMLElement>("#watershed-info")!;
const stSection = document.querySelector<HTMLElement>("#stations-section")!;

const map = createMap(mapEl);
const layers = new WatershedLayers(map);

map.on("click", async (e) => {
  const { lat, lng } = e.latlng;
  statusEl.textContent = `Delineando em (${lat.toFixed(4)}, ${lng.toFixed(4)})…`;

  try {
    const result = await api.delineate(lat, lng, "auto");
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

    statusEl.textContent = "Buscando estações da ANA…";
    try {
      const stations = await api.stations(result.watershed);
      renderStations(stations.pluviometricas, stations.fluviometricas);
      statusEl.textContent = "Pronto.";
    } catch (err) {
      stSection.innerHTML = `<h2>Estações</h2><p class="muted">${(err as Error).message}</p>`;
      statusEl.textContent = "Bacia OK, mas falhou o cruzamento de estações.";
    }
  } catch (err) {
    statusEl.textContent = `Erro: ${(err as Error).message}`;
  }
});

function renderStations(pluv: Station[], fluv: Station[]) {
  const section = stSection;
  const mkRow = (s: Station) => `
    <div class="station-row">
      <span>${s.codigo} <small class="muted">${s.tipo[0]}</small></span>
      <button data-codigo="${s.codigo}" data-kind="${s.tipo === "Pluviométrica" ? "chuva" : "vazao"}">baixar</button>
    </div>`;

  section.innerHTML = `
    <h2>Estações (${pluv.length + fluv.length})</h2>
    <div><small class="muted">${pluv.length} pluviométricas · ${fluv.length} fluviométricas</small></div>
    <div>${[...pluv, ...fluv].map(mkRow).join("")}</div>
  `;

  section.querySelectorAll("button[data-codigo]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const codigo = (btn as HTMLButtonElement).dataset.codigo!;
      const kind = (btn as HTMLButtonElement).dataset.kind!;
      (btn as HTMLButtonElement).disabled = true;
      try {
        const { job_id } = await api.enqueueDownload({
          codigo_estacao: codigo,
          kind,
          ano_inicial: 1900,
          ano_final: 2025,
        });
        statusEl.textContent = `Job enfileirado: ${job_id}`;
      } catch (err) {
        statusEl.textContent = `Falha ao enfileirar: ${(err as Error).message}`;
        (btn as HTMLButtonElement).disabled = false;
      }
    });
  });
}
