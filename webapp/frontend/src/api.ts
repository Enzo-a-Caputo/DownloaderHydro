export interface DelineateResponse {
  watershed: GeoJSON.Feature;
  rivers: GeoJSON.FeatureCollection | null;
  area_km2: number;
  lat_snap: number;
  lng_snap: number;
  snap_dist_m: number;
  basin_pfaf2: number;
  mode: "high" | "low";
}

export interface Station {
  codigo: string;
  tipo: "Pluviométrica" | "Fluviométrica";
  lat: number;
  lng: number;
  nome: string | null;
}

export interface StationsResponse {
  pluviometricas: Station[];
  fluviometricas: Station[];
}

export interface Job {
  id: string;
  kind: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  codigo_estacao?: string;
  output_path?: string | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  async delineate(lat: number, lng: number, precision: "high" | "low" | "auto" = "auto") {
    return j<DelineateResponse>(await fetch("/api/delineate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lng, precision }),
    }));
  },

  async stations(watershed: GeoJSON.Feature) {
    return j<StationsResponse>(await fetch("/api/stations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ watershed }),
    }));
  },

  async enqueueDownload(params: {
    codigo_estacao: string;
    kind: string;
    ano_inicial: number;
    ano_final: number;
    identificador?: string;
    senha?: string;
  }) {
    return j<{ job_id: string; status: string }>(await fetch("/api/downloads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }));
  },

  async jobs() {
    return j<Job[]>(await fetch("/api/jobs"));
  },

  async job(id: string) {
    return j<Job>(await fetch(`/api/jobs/${id}`));
  },

  jobDownloadUrl(id: string) {
    return `/api/jobs/${id}/download`;
  },
};
