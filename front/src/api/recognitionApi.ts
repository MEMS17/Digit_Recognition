import type { ApiPredictionResponse, RecognitionResult } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

export class ApiRequestError extends Error {}

const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

const mockMailResponse: ApiPredictionResponse = {
  prediction_id: 'demo-postal-001', task: 'postal_code', value: '75013', status: 'needs_review', score: .74,
  bbox: { x: 0, y: 0, width: 800, height: 180 }, image: { width: 800, height: 180 },
  model_version: 'postal-demo-v1', preprocessing_version: 'postal-demo-preprocessing-v1', reasons: ['low_score'],
  reference_check: { status: 'not_checked', version: null }, created_at: '2026-09-30T08:00:00Z', review_token: 'demo-review-token', review: null,
};
const mockDigitResponse: ApiPredictionResponse = {
  prediction_id: 'demo-digit-001', task: 'digit', value: '8', status: 'recognized', score: .93,
  bbox: { x: 0, y: 0, width: 560, height: 300 }, image: { width: 560, height: 300 },
  model_version: 'digit-demo-v1', preprocessing_version: 'digit-demo-preprocessing-v1', reasons: [],
  reference_check: { status: 'not_applicable', version: null }, created_at: '2026-09-30T08:00:00Z', review_token: 'demo-review-token', review: null,
};

function confidenceLevel(score: number | null): RecognitionResult['confidenceLevel'] {
  if (score === null) return 'low';
  if (score >= .9) return 'high';
  if (score >= .7) return 'medium';
  return 'low';
}

export function adaptPrediction(response: ApiPredictionResponse, reviewToken?: string): RecognitionResult {
  const displayedValue = response.review?.corrected_value ?? response.value;
  const value = response.value ?? '';
  return {
    kind: response.task === 'postal_code' ? 'postal-code' : 'digit', value: displayedValue,
    originalValue: response.value, confidence: response.score, confidenceLevel: confidenceLevel(response.score),
    requiresManualReview: response.status !== 'recognized' && !response.review,
    predictions: value.split('').map((digit) => ({ digit, confidence: response.score })),
    predictionId: response.prediction_id, reviewToken, status: response.status, reasons: response.reasons,
    modelVersion: response.model_version, preprocessingVersion: response.preprocessing_version, createdAt: response.created_at,
    review: response.review ? { correctedValue: response.review.corrected_value, reviewedAt: response.review.reviewed_at } : null,
    detectedZone: response.bbox,
  };
}

async function errorFromResponse(response: Response): Promise<ApiRequestError> {
  let message = 'Le service de reconnaissance est momentanément indisponible.';
  try {
    const body = await response.json() as { error?: { message?: string } };
    message = body.error?.message ?? message;
  } catch { /* A proxy may return a non-JSON error page. */ }
  return new ApiRequestError(message);
}

async function postImage(path: string, image: Blob, inputKind?: 'crop'): Promise<RecognitionResult> {
  const formData = new FormData();
  formData.append('image', image, image instanceof File ? image.name : 'drawing.png');
  if (inputKind) formData.append('input_kind', inputKind);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', body: formData });
    if (!response.ok) throw await errorFromResponse(response);
    const payload = await response.json() as ApiPredictionResponse;
    return adaptPrediction(payload, payload.review_token);
  } catch (error) {
    if (error instanceof ApiRequestError) throw error;
    throw new ApiRequestError('Le service de reconnaissance est momentanément indisponible.');
  }
}

export async function recognizeMail(image: Blob): Promise<RecognitionResult> {
  if (!USE_MOCKS) return postImage('/v1/predictions/postal-code/', image, 'crop');
  await wait(900);
  return adaptPrediction(mockMailResponse, mockMailResponse.review_token);
}

export async function recognizeDigit(image: Blob): Promise<RecognitionResult> {
  if (!USE_MOCKS) return postImage('/v1/predictions/digit/', image);
  await wait(650);
  return adaptPrediction(mockDigitResponse, mockDigitResponse.review_token);
}

export async function submitReview(result: RecognitionResult, correctedValue: string): Promise<RecognitionResult> {
  if (USE_MOCKS) {
    await wait(350);
    return { ...result, value: correctedValue, review: { correctedValue, reviewedAt: new Date().toISOString() }, requiresManualReview: false };
  }
  if (!result.predictionId || !result.reviewToken) throw new ApiRequestError('Le jeton de révision n’est plus disponible pour cette lecture.');
  try {
    const response = await fetch(`${API_BASE_URL}/v1/predictions/${result.predictionId}/review/`, {
      method: 'PATCH', headers: { Authorization: `Bearer ${result.reviewToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ corrected_value: correctedValue }),
    });
    if (!response.ok) throw await errorFromResponse(response);
    return adaptPrediction(await response.json() as ApiPredictionResponse, result.reviewToken);
  } catch (error) {
    if (error instanceof ApiRequestError) throw error;
    throw new ApiRequestError('La correction n’a pas pu être enregistrée.');
  }
}
