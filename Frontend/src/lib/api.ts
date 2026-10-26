import {
  User,
  GameItem,
  AnswerResult,
  ResearchItem,
  ResearchSubmissionResult,
  DetectionResult,
  PresetSample,
  PerformanceMetrics,
  QuadrantItem,
  LeaderboardEntry
} from './types';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window!=='undefined'&&['localhost','127.0.0.1'].includes(window.location.hostname)?`${window.location.protocol}//${window.location.hostname}:8000`:'https://api.deepshield.nahin.com.bd');

export function apiFetch(input: RequestInfo | URL, init?: RequestInit) { return fetch(input, {...init, signal: init?.signal ?? AbortSignal.timeout(240_000), credentials: "include"}); }

async function requestAuth(path: string, body: Record<string, string>): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const response = await res.json().catch(() => null);
    const detail = response?.detail;
    const message = Array.isArray(detail)
      ? detail.map((issue: { msg?: string }) => issue.msg).filter(Boolean).join(' ')
      : detail;
    throw new Error(typeof message === 'string' ? message : 'Authentication failed');
  }
  return res.json();
}

export function loginUser(username: string, password: string): Promise<User> {
  return requestAuth('login', { username, password });
}

export function registerUser(username: string, displayName: string, password: string, email: string, language: string): Promise<{verification_required:boolean}> {
  return requestAuth('signup', { username, display_name: displayName, password, email, language });
}

export async function getUserProfile(userId: number): Promise<User> {
  const res = await apiFetch(`${API_BASE}/api/auth/user/${userId}`);
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to fetch user profile'); }
  return res.json();
}

// --- Game Endpoints ---
export async function getGameItems(count: number = 5): Promise<GameItem[]> {
  const res = await apiFetch(`${API_BASE}/api/game/items?count=${count}`);
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to fetch game items'); }
  return res.json();
}

export async function submitRoundAnswer(
  userId: number,
  itemId: number,
  prediction: string,
  timeTakenMs: number,
  roomCode?: string,
  ticket?: string
): Promise<AnswerResult> {
  const res = await apiFetch(`${API_BASE}/api/game/submit-round`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticket,
      user_id: userId,
      item_id: itemId,
      prediction,
      time_taken_ms: timeTakenMs,
      room_code: roomCode
    })
  });
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to submit answer'); }
  return res.json();
}

export async function completeGameSession(userId: number, rounds: any[]): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/game/complete-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, rounds })
  });
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to complete session'); }
  return res.json();
}

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  const res = await apiFetch(`${API_BASE}/api/game/leaderboard`);
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to fetch leaderboard'); }
  return res.json();
}

// --- Multiplayer Rooms ---
export async function createRoom(userId: number, totalRounds: number = 5): Promise<{ room_code: string; room_id: number }> {
  const res = await apiFetch(`${API_BASE}/api/rooms/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, total_rounds: totalRounds })
  });
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to create room'); }
  return res.json();
}

export async function joinRoom(roomCode: string, userId: number, displayName: string): Promise<any> {
  const res = await apiFetch(`${API_BASE}/api/rooms/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ room_code: roomCode, user_id: userId, display_name: displayName })
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to join room');
  }
  return res.json();
}

// --- Research Challenge ---
export async function getResearchItems(userId: number): Promise<ResearchItem[]> {
  const res = await apiFetch(`${API_BASE}/api/research/items?user_id=${userId}`);
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to fetch research items');
  }
  return res.json();
}

export async function submitResearchEvaluation(
  userId: number,
  itemId: number,
  humanPrediction: string,
  humanConfidence: number,
  clueTags: string[],
  reactionTimeMs: number
): Promise<ResearchSubmissionResult> {
  const res = await apiFetch(`${API_BASE}/api/research/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      item_id: itemId,
      human_prediction: humanPrediction,
      human_confidence: humanConfidence,
      clue_tags: clueTags,
      reaction_time_ms: reactionTimeMs
    })
  });
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to submit research evaluation'); }
  return res.json();
}

// --- AI Detector ---
export async function getPresetSamples(): Promise<PresetSample[]> {
  const res = await apiFetch(`${API_BASE}/api/detector/presets`);
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to fetch presets'); }
  return res.json();
}

export async function analyzePreset(sampleId: string): Promise<DetectionResult> {
  const res = await apiFetch(`${API_BASE}/api/detector/analyze-preset/${sampleId}`, {
    method: 'POST'
  });
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to analyze preset'); }
  return res.json();
}

export async function uploadAndDetect(file: File): Promise<DetectionResult> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await apiFetch(`${API_BASE}/api/detector/upload`, {
    method: 'POST',
    body: formData
  });
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to analyze uploaded media'); }
  return res.json();
}

// --- Dashboard & Analytics ---
export async function getDashboardMetrics(): Promise<PerformanceMetrics> {
  const res = await apiFetch(`${API_BASE}/api/dashboard/metrics`);
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to fetch metrics'); }
  return res.json();
}

export async function getQuadrantItems(quadrant: string): Promise<QuadrantItem[]> {
  const res = await apiFetch(`${API_BASE}/api/dashboard/quadrants/${quadrant}`);
  if (!res.ok) { const err = await res.json().catch(() => null); throw new Error(typeof err?.detail === 'string' ? err.detail : 'Failed to fetch quadrant items'); }
  return res.json();
}

export function getExportCsvUrl(): string {
  return `${API_BASE}/api/dashboard/export/csv`;
}

export function getExportJsonUrl(): string {
  return `${API_BASE}/api/dashboard/export/json`;
}

export function getMediaUrl(path: string): string {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }
  return `${API_BASE}${path}`;
}

export async function adminRequest(path: string, body?: unknown, method = 'POST') {
  const res = await apiFetch(`${API_BASE}/api/admin${path}`, body === undefined ? {} : {method, headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await res.json();
  if(!res.ok) throw new Error(typeof data.detail==='string'?data.detail:'Request failed');
  return data;
}

export function loginAdmin(username:string,password:string):Promise<User>{return requestAuth('admin/login',{username,password});}
export async function memberRequest(path:string, body?:unknown, method='POST') {
 const res=await apiFetch(`${API_BASE}/api/profile${path}`,body===undefined?{}:{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await res.json();if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'Request failed');return data;
}
