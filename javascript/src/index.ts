/**
 * Mnemonic SDK
 * 
 * Official JavaScript/TypeScript SDK for Mnemonic
 * Persistent cognitive infrastructure for AI agents
 * 
 * @example
 * ```typescript
 * import { Mnemonic } from '@mnemonicai.official/sdk-js';
 * 
 * const mnemonic = new Mnemonic({ apiKey: 'mnemo_sk_...' });
 * 
 * // Recall before task
 * const memory = await mnemonic.recall({
 *   agentId: 'agent-123',
 *   task: 'Deploy to production'
 * });
 * 
 * // Capture after task
 * await mnemonic.capture({
 *   agentId: 'agent-123',
 *   task: 'Deploy to production',
 *   actions: [...],
 *   output: 'Success',
 *   success: true
 * });
 * ```
 */

export { Mnemonic, Mnemonic as default } from './client';

export {
  MnemonicError,
  AuthError,
  NotFoundError,
  RateLimitError,
  ValidationError,
} from './errors';

export type {
  MnemonicConfig,
  Action,
  RecallRequest,
  RecallResponse,
  LessonHit,
  ProcedureHit,
  CaptureRequest,
  CaptureResponse,
  CreateAgentRequest,
  Agent,
  AgentStats,
  Lesson,
  Procedure,
  FeedbackRequest,
  LessonOutcome,
  ImprovementMetrics,
  LessonEffectivenessReport,
  LessonEffectivenessResponse,
  LessonAnalytics,
  NetworkEffectsStats,
} from './types';
