export type Confidence = 'high' | 'medium' | 'low';

export interface DigitPrediction { digit: string; confidence: number | null; }

export interface Review { correctedValue: string; reviewedAt: string; }

export interface RecognitionResult {
  kind: 'digit' | 'postal-code';
  value: string | null;
  originalValue: string | null;
  confidence: number | null;
  confidenceLevel: Confidence;
  requiresManualReview: boolean;
  predictions: DigitPrediction[];
  predictionId?: string;
  reviewToken?: string;
  status: 'recognized' | 'needs_review' | 'unreadable';
  reasons: string[];
  modelVersion?: string;
  preprocessingVersion?: string;
  createdAt?: string;
  review?: Review | null;
  detectedZone?: { x: number; y: number; width: number; height: number } | null;
}

export interface ApiPredictionResponse {
  prediction_id: string;
  task: 'digit' | 'postal_code';
  value: string | null;
  status: 'recognized' | 'needs_review' | 'unreadable';
  score: number | null;
  bbox: { x: number; y: number; width: number; height: number } | null;
  image: { width: number; height: number };
  model_version: string;
  preprocessing_version: string;
  reasons: string[];
  reference_check: { status: string; version: string | null };
  created_at: string;
  review_token?: string;
  review: { corrected_value: string; reviewed_at: string } | null;
}
