export interface User {
  id: number;
  username: string;
  display_name: string;
  role: 'participant' | 'researcher' | 'admin';
  score: number;
  games_played: number;
  total_correct: number;
  total_rounds_played: number;
  accuracy: number;
  qualified_for_research: boolean;
  has_password?: boolean;
  needs_profile?: boolean;
}

export interface GameItem {
  ticket?: string;
  id: number;
  title: string;
  media_type: string;
  media_url: string;
  difficulty: string;
  description: string;
}

export interface AnswerResult {
  ai_prediction?: string | null;
  ai_confidence?: number | null;
  ai_error?: string | null;
  item_id: number;
  is_correct: boolean;
  ground_truth: string;
  points_awarded: number;
  explanation: string;
  visual_cues: string[];
  manipulation_type: string;
}

export interface ResearchItem {
  id: number;
  title: string;
  media_type: string;
  media_url: string;
  thumbnail_url?: string;
  manipulation_type: string;
  difficulty: string;
  description: string;
  visual_cues: string[];
}

export interface ResearchSubmissionResult {
  submission_id: number;
  item_id: number;
  ground_truth: string;
  human_prediction: string;
  human_confidence: number;
  is_human_correct: boolean;
  ai_prediction: string;
  ai_confidence: number;
  is_ai_correct: boolean;
  disagreement_quadrant: 'Q1' | 'Q2' | 'Q3' | 'Q4';
  quadrant_description: string;
  explanation: string;
  xai_heatmap_url?: string;
  temporal_anomaly_scores: number[];
}

export interface DetectionResult {
  media_type?: 'video' | 'image';
  analysis_mode?: 'video_sequence' | 'repeated_still_experimental';
  experimental?: boolean;
  analysis_warning?: string | null;
  temporal_analysis_available?: boolean;
  detection_id?: number;
  detected_frames?:number;
  repeated_frames?:number;
  frame_details?: {position:number;source_frame:number;timestamp:number|null;image:string;overlay:string;sensitivity:number;repeated:boolean}[];
  focus_frame?:number|null;
  xai_error?: string | null;
  model_id?: string | null;
  checkpoint_epoch?: number | null;
  verdict: 'Real' | 'Fake';
  fake_probability: number;
  confidence_percentage: number;
  model_name: string;
  model_checkpoint_loaded: boolean;
  spatial_heatmap_base64?: string;
  temporal_scores: number[];
  detected_artifacts: string[];
  verification_tips: string[];
}

export interface PresetSample {
  id: string;
  title: string;
  category: string;
  thumbnail: string;
}

export interface PerformanceMetrics {
  total_evaluations: number;
  human_accuracy: number;
  human_precision: number;
  human_recall: number;
  human_f1: number;
  ai_accuracy: number;
  ai_precision: number;
  ai_recall: number;
  ai_f1: number;
  hybrid_accuracy: number;
  human_confusion_matrix: { TP: number; FP: number; TN: number; FN: number };
  ai_confusion_matrix: { TP: number; FP: number; TN: number; FN: number };
  quadrant_breakdown: { Q1: number; Q2: number; Q3: number; Q4: number };
  calibration_data: Array<{
    confidence_level: number;
    confidence_label: string;
    expected_accuracy: number;
    actual_accuracy: number;
    sample_count: number;
  }>;
}

export interface QuadrantItem {
  submission_id: number;
  item_id: number;
  title: string;
  media_url: string;
  ground_truth: string;
  human_prediction: string;
  human_confidence: number;
  is_human_correct: boolean;
  ai_prediction: string;
  ai_confidence: number;
  is_ai_correct: boolean;
  disagreement_quadrant: 'Q1' | 'Q2' | 'Q3' | 'Q4';
  reaction_time_ms: number;
  clue_tags: string[];
  temporal_anomaly_scores: number[];
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  display_name: string;
  score: number;
  games_played: number;
  accuracy: number;
  qualified: boolean;
}
