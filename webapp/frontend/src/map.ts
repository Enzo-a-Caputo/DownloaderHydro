import L from "leaflet";

const BASEMAPS: Record<string, L.TileLayer> = {
  "OpenStreetMap": L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { attribution: "© OpenStreetMap", maxZoom: 19 }
  ),
  "Google Satellite": L.tileLayer(
    "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
    { attribution: "© Google", maxZoom: 21 }
  ),
  "Google Hybrid": L.tileLayer(
    "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    { attribution: "© Google", maxZoom: 21 }
  ),
  "Esri World Imagery": L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "© Esri, Maxar, Earthstar Geographics", maxZoom: 19 }
  ),
  "OpenTopoMap": L.tileLayer(
    "https://tile.opentopomap.org/{z}/{x}/{y}.png",
    { attribution: "© OpenTopoMap (CC-BY-SA)", maxZoom: 17 }
  ),
};

// ── Popup com todos os campos da estação ──────────────────────────────────────
function stationPopupHtml(props: Record<string, unknown>): string {
  const skip = new Set(["geometry", "lat", "lng", "UF"]);
  const rows = Object.entries(props)
    .filter(([k, v]) => !skip.has(k) && v !== null && v !== "" && v !== "None")
    .map(([k, v]) => `<tr><td class="pk">${k}</td><td>${v}</td></tr>`)
    .join("");
  return `<div class="station-popup"><table>${rows}</table></div>`;
}

// ── Cores por tipo ────────────────────────────────────────────────────────────
function stationColor(tipo: string): string {
  if (tipo?.includes("Pluvi")) return "#3fb950";
  if (tipo?.includes("Fluvi")) return "#f85149";
  return "#aaa";
}

// ── Camada de inventário global ───────────────────────────────────────────────
// Usa L.geoJSON com canvas renderer — aguenta dezenas de milhares de pontos
// sem travar o browser (vs. criar N objetos circleMarker individualmente).
export class InventoryLayer {
  private layer: L.GeoJSON | null = null;
  private fc: GeoJSON.FeatureCollection | null = null;
  private _count = 0;
  private renderer = L.canvas({ padding: 0.5 });

  constructor(private map: L.Map) {}

  load(fc: GeoJSON.FeatureCollection) {
    if (this.layer) { this.map.removeLayer(this.layer); this.layer = null; }
    this.fc = fc;
    this._count = fc.features.length;
    this._build(fc.features);
  }

  private _build(features: GeoJSON.Feature[]) {
    if (this.layer) { this.map.removeLayer(this.layer); }
    const renderer = this.renderer;
    this.layer = L.geoJSON({ type: "FeatureCollection", features } as GeoJSON.FeatureCollection, {
      pointToLayer: (f, latlng) => {
        const tipo = String((f.properties as Record<string, unknown>)["TIPOESTACA"] ?? "");
        return L.circleMarker(latlng, {
          renderer,
          radius: 4,
          color: stationColor(tipo),
          fillColor: stationColor(tipo),
          fillOpacity: 0.75,
          weight: 0.6,
        });
      },
      onEachFeature: (f, layer) => {
        const p = f.properties as Record<string, unknown>;
        layer.bindPopup(stationPopupHtml(p), { maxWidth: 300, maxHeight: 360 });
      },
    }).addTo(this.map);
  }

  applyFilter(tipos: Set<string>, dtypes: Set<string>, apenasAtivas: boolean) {
    if (!this.fc) return;
    const wantPlu = tipos.has("Pluviométrica");
    const wantFlu = tipos.has("Fluviométrica");
    const filtered = this.fc.features.filter(f => {
      const p        = f.properties as Record<string, unknown>;
      const tipo     = String(p["TIPOESTACA"] ?? "");
      const operando = String(p["Operando"] ?? "");
      const isPlu    = tipo.includes("Pluvi");
      const isFlu    = tipo.includes("Fluvi");
      const tipoOk   = tipos.size === 0 || (wantPlu && isPlu) || (wantFlu && isFlu);
      const ativaOk  = !apenasAtivas || operando === "1";
      const dtypeOk  = dtypes.size === 0 || [...dtypes].every(col => String(p[col] ?? "0") === "1");
      return tipoOk && ativaOk && dtypeOk;
    });
    this._build(filtered);
  }

  get count() { return this._count; }
}


// ── Camada da bacia delineada ─────────────────────────────────────────────────
export class WatershedLayers {
  private watershed: L.GeoJSON | null = null;
  private rivers: L.GeoJSON | null = null;
  private outletMarker: L.Marker | null = null;
  private snapMarker: L.CircleMarker | null = null;

  constructor(private map: L.Map) {}

  clear() {
    for (const l of [this.watershed, this.rivers, this.outletMarker, this.snapMarker]) {
      if (l) this.map.removeLayer(l);
    }
    this.watershed = this.rivers = null;
    this.outletMarker = this.snapMarker = null;
  }

  show(params: {
    watershed: GeoJSON.Feature;
    rivers: GeoJSON.FeatureCollection | null;
    outlet: [number, number];
    snap: [number, number];
  }) {
    this.clear();
    this.watershed = L.geoJSON(params.watershed, {
      style: { color: "#4f8cff", weight: 2, fillOpacity: 0.15 },
    }).addTo(this.map);

    if (params.rivers) {
      this.rivers = L.geoJSON(params.rivers, {
        style: { color: "#2aa9ff", weight: 1.2, opacity: 0.85 },
      }).addTo(this.map);
    }

    this.outletMarker = L.marker(params.outlet).addTo(this.map).bindPopup("Ponto clicado");
    this.snapMarker   = L.circleMarker(params.snap, {
      radius: 5, color: "#00d28a", fillColor: "#00d28a", fillOpacity: 1,
    }).addTo(this.map).bindPopup("Exutório ajustado (snap)");

    const bounds = this.watershed.getBounds();
    if (bounds.isValid()) this.map.fitBounds(bounds, { padding: [40, 40] });
  }
}


// ── Criação do mapa ───────────────────────────────────────────────────────────
export function createMap(el: HTMLElement): L.Map {
  const map = L.map(el, {
    center: [-15, -60],
    zoom: 4,
    worldCopyJump: true,
    layers: [BASEMAPS["OpenStreetMap"]],
  });
  L.control.layers(BASEMAPS, {}, { position: "topright", collapsed: true }).addTo(map);
  return map;
}
