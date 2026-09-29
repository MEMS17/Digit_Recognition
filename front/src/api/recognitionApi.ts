import type { RecognitionResult } from './types';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== 'false';
export class ApiUnavailableError extends Error {}
const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
const mockMailResult: RecognitionResult = { kind: 'postal-code', value: '75013', confidence: .74, confidenceLevel: 'medium', requiresManualReview: true, predictions: [{ digit: '7', confidence: .96 }, { digit: '5', confidence: .89 }, { digit: '0', confidence: .99 }, { digit: '1', confidence: .62 }, { digit: '3', confidence: .71 }], detectedZone: { x: 29, y: 37, width: 45, height: 18 } };
const mockDigitResult: RecognitionResult = { kind: 'digit', value: '8', confidence: .93, confidenceLevel: 'high', requiresManualReview: false, predictions: [{ digit: '8', confidence: .93 }] };
async function postImage(path: string, image: Blob): Promise<RecognitionResult> { const formData = new FormData(); formData.append('image', image, 'image.png'); try { const response = await fetch(`${API_BASE_URL}${path}`, { method: 'POST', body: formData }); if (!response.ok) throw new ApiUnavailableError(); return response.json() as Promise<RecognitionResult>; } catch (error) { if (error instanceof ApiUnavailableError) throw error; throw new ApiUnavailableError(); } }
export async function recognizeMail(image: Blob): Promise<RecognitionResult> { if (!USE_MOCKS) return postImage('/recognitions/mail/', image); await wait(900); return mockMailResult; }
export async function recognizeDigit(image: Blob): Promise<RecognitionResult> { if (!USE_MOCKS) return postImage('/recognitions/digit/', image); await wait(650); return mockDigitResult; }
