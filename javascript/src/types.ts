/**
 * Mnemonic SDK Types
 */

export interface MnemonicConfig {
  apiKey?: string;
  baseUrl?: string;
  timeout?: number;
}

export interface Action {
  type: string;
  target?: string;
  result?: string;
  [key: string]: any;
}

export interface RecallRequest {
  agentId: string;
  task: string;
  limit?: number;
  context?: Record<string, any>;
  asPrompt?: boolean;
}

export interface LessonHit {
  id: string;
  content: string;
  lessonType?: string;
  confidence: number;
  similarity: float;
  contextSimilarity: number;
  finalScore: number;
  qualityScore?: number;
  usageCount?: number;
  source?: 'own' | 'team' | 'global';
  isStale: boolean;
  isDeprecated: boolean;
  // Structured fields
  domain?: string;
  subdomain?: string;
  problemType?: string;
  problemSignature?: string;
  rootCause?: string;
  solutionSteps?: string[];
  validationSteps?: string[];
  failureSignals?: string[];
}

export interface ProcedureHit {
  id: string;
  name: string;
  description?: string;
  steps: string[];
  confidence: number;
  successCount: number;
  failureCount: number;
  similarity: number;
}

export interface RecallResponse {
  lessons: LessonHit[];
  procedures: ProcedureHit[];
  contextPrompt?: string;
  warnings: string[];
}

export interface CaptureRequest {
  agentId: string;
  task: string;
  actions: Action[];
  output: string;
  success: boolean;
  timeTaken?: number;
  retries?: number;
  metadata?: Record<string, any>;
}

export interface CaptureResponse {
  id: string;
  status: string;
  [key: string]: any;
}

export interface CreateAgentRequest {
  externalId: string;
  name?: string;
  description?: string;
  metadata?: Record<string, any>;
}

export interface Agent {
  id: string;
  tenantId: string;
  externalId: string;
  name?: string;
  description?: string;
  metadata?: Record<string, any>;
  totalTasks: number;
  createdAt: string;
}

export interface AgentStats {
  agentId: string;
  totalTasks: number;
  successRate: number;
  avgTimeTaken: number;
  totalLessons: number;
  totalProcedures: number;
}

export interface Lesson {
  id: string;
  content: string;
  lessonType?: string;
  confidence: number;
  problemSignature?: string;
  rootCause?: string;
  solutionSteps?: string[];
  [key: string]: any;
}

export interface Procedure {
  id: string;
  name: string;
  description?: string;
  steps: string[];
  confidence: number;
  successCount: number;
  failureCount: number;
  [key: string]: any;
}

export interface FeedbackRequest {
  rating: string;
  lessonId?: string;
  procedureId?: string;
  comment?: string;
}

export type LessonOutcome = 'success' | 'failure' | 'partial';

export interface ImprovementMetrics {
  timeSavedMs?: number;
  retriesReduced?: number;
  errorsAvoided?: number;
  [key: string]: any;
}

export interface LessonEffectivenessReport {
  lessonId: string;
  agentId: string;
  task: string;
  outcome: LessonOutcome;
  improvementMetrics?: ImprovementMetrics;
}

export interface LessonEffectivenessResponse {
  status: string;
  lessonId: string;
  outcome: LessonOutcome;
  crossTenant: boolean;
}

export interface LessonAnalytics {
  lessonId: string;
  content: string;
  qualityScore: number;
  usageCount: number;
  successCount: number;
  failureCount: number;
  successRate: number;
  createdByTenantId?: string;
  createdByAgentId?: string;
  reinforcementCount: number;
  contradictionCount: number;
}

export interface NetworkEffectsStats {
  totalLessons: number;
  publicLessons: number;
  privateLessons: number;
  totalUsageEvents: number;
  avgQualityScore: number;
  topLessons: LessonAnalytics[];
  crossTenantLearningEvents: number;
}
