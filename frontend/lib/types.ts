export type Quadrant = "Leading" | "Weakening" | "Lagging" | "Improving" | "Unknown";

export interface RRGPoint {
  date: string;
  rs_ratio: number | null;
  rs_momentum: number | null;
  quadrant: Quadrant;
  rvol: number | null;
  fund_score: number | null;
}

export interface RRGSeries {
  ticker: string;
  is_etf: boolean;
  points: RRGPoint[];
}

export interface RRGResponse {
  benchmark: string;
  n: number;
  asOf: string | null;
  series: RRGSeries[];
}

export interface SectorInfo {
  name: string;
  components: string[];
}

export interface SectorsResponse {
  benchmark: string;
  sectors: Record<string, SectorInfo>;
}

export interface Session {
  id: string;
  title: string;
  universe: string[];
  benchmark: string;
  n: number;
  tail: number;
  startDate: string;
  currentDate: string | null;
  createdAt: number;
}
