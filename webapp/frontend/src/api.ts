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
  tipo: string;
  lat: number;
  lng: number;
  nome: string | null;
  props: Record<string, unknown>;
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

export interface AuthStatus {
  authenticated: boolean;
  identificador: string | null;
}

// Erro especial para respostas 401 — o frontend usa para mostrar o login
export class UnauthorizedError extends Error {
  constructor() { super("Não autenticado"); }
}

async function j<T>(res: Response): Promise<T> {
  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  async authMe() {
    return j<AuthStatus>(await fetch("/api/auth/me", { credentials: "include" }));
  },

  async login(identificador: string, senha: string) {
    return j<AuthStatus>(await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ identificador, senha }),
    }));
  },

  async logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
  },

  async inventory() {
    return j<GeoJSON.FeatureCollection>(await fetch("/api/inventory", { credentials: "include" }));
  },

  async delineate(
    lat: number, lng: number,
    precision: "high" | "low" | "auto" = "auto",
    snap_sensitivity: "auto" | "medium" | "small" | "micro" = "auto",
  ) {
    return j<DelineateResponse>(await fetch("/api/delineate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ lat, lng, precision, snap_sensitivity }),
    }));
  },

  async stations(watershed: GeoJSON.Feature) {
    return j<StationsResponse>(await fetch("/api/stations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ watershed }),
    }));
  },

  async enqueueDownload(params: {
    codigo_estacao: string; kind: string;
    ano_inicial: number; ano_final: number;
  }) {
    return j<{ job_id: string; status: string }>(await fetch("/api/downloads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(params),
    }));
  },

  async jobs() { return j<Job[]>(await fetch("/api/jobs", { credentials: "include" })); },
  async job(id: string) { return j<Job>(await fetch(`/api/jobs/${id}`, { credentials: "include" })); },
  jobDownloadUrl(id: string) { return `/api/jobs/${id}/download`; },
};
