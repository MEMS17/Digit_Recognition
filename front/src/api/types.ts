export type Confidence = 'high' | 'medium' | 'low';
export interface DigitPrediction { digit: string; confidence: number; }
export interface RecognitionResult { kind: 'digit' | 'postal-code'; value: string; confidence: number; confidenceLevel: Confidence; requiresManualReview: boolean; predictions: DigitPrediction[]; detectedZone?: { x: number; y: number; width: number; height: number }; }
