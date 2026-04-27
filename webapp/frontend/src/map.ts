import L from "leaflet";

export function createMap(el: HTMLElement): L.Map {
  // Foco inicial na América do Sul (centro aproximado + zoom baixo)
  const map = L.map(el, {
    center: [-15, -60],
    zoom: 4,
    worldCopyJump: true,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
    maxZoom: 19,
  }).addTo(map);

  return map;
}

export class WatershedLayers {
  private watershed: L.GeoJSON | null = null;
  private rivers: L.GeoJSON | null = null;
  private outletMarker: L.Marker | null = null;
  private snapMarker: L.CircleMarker | null = null;

  constructor(private map: L.Map) {}

  clear() {
    for (const layer of [this.watershed, this.rivers, this.outletMarker, this.snapMarker]) {
      if (layer) this.map.removeLayer(layer);
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
    this.snapMarker = L.circleMarker(params.snap, {
      radius: 5, color: "#00d28a", fillColor: "#00d28a", fillOpacity: 1,
    }).addTo(this.map).bindPopup("Exutório ajustado (snap)");

    const bounds = this.watershed.getBounds();
    if (bounds.isValid()) this.map.fitBounds(bounds, { padding: [40, 40] });
  }

  showStations(pluv: L.LatLngExpression[], fluv: L.LatLngExpression[]) {
    for (const p of pluv) {
      L.circleMarker(p, { radius: 4, color: "#3fb950", fillColor: "#3fb950", fillOpacity: 1 })
        .addTo(this.map);
    }
    for (const p of fluv) {
      L.circleMarker(p, { radius: 4, color: "#f85149", fillColor: "#f85149", fillOpacity: 1 })
        .addTo(this.map);
    }
  }
}
