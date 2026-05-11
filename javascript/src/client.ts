/**
 * Mnemonic JavaScript/TypeScript SDK
 * 
 * Persistent cognitive infrastructure for AI agents
 */

import type {
  MnemonicConfig,
  RecallRequest,
  RecallResponse,
  CaptureRequest,
  CaptureResponse,
  CreateAgentRequest,
  Agent,
  AgentStats,
  Lesson,
  Procedure,
  FeedbackRequest,
  LessonEffectivenessReport,
  LessonEffectivenessResponse,
  LessonAnalytics,
  NetworkEffectsStats,
} from './types';

import {
  MnemonicError,
  AuthError,
  NotFoundError,
  RateLimitError,
  ValidationError,
} from './errors';

export class Mnemonic {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;

  constructor(config: MnemonicConfig = {}) {
    this.apiKey = config.apiKey || process.env.MNEMO_API_KEY || '';
    
    if (!this.apiKey) {
      throw new Error(
        'API key required. Pass apiKey in config or set MNEMO_API_KEY environment variable.'
      );
    }

    this.baseUrl = (config.baseUrl || 'https://api.mnemo.dev').replace(/\/$/, '');
    this.timeout = config.timeout || 30000;
  }

  /**
   * Make HTTP request to Mnemonic API
   */
  private async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    
    const headers: Record<string, string> = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      'User-Agent': 'mnemonic-js/0.2.0',
    };

    const options: RequestInit = {
      method,
      headers,
      signal: AbortSignal.timeout(this.timeout),
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(url, options);
      
      if (!response.ok) {
        await this.handleError(response);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      const data = await response.json();
        return data as T;

    } catch (error: any) {
      if (error instanceof MnemonicError) {
        throw error;
      }
      throw new MnemonicError(
        error.message || 'Request failed',
        undefined,
        error
      );
    }
  }

  /**
   * Handle API errors
   */
  private async handleError(response: Response): Promise<never> {
    let detail: string;
    
    try {
  const data = await response.json() as { detail?: string };
  detail = data.detail || response.statusText;
    } catch {
      detail = response.statusText;
    }

    switch (response.status) {
      case 401:
        throw new AuthError(detail);
      case 404:
        throw new NotFoundError(detail);
      case 422:
        throw new ValidationError(detail);
      case 429:
        throw new RateLimitError(detail);
      default:
        throw new MnemonicError(
          `HTTP ${response.status}: ${detail}`,
          response.status
        );
    }
  }

  // ================================================================
  // CORE METHODS
  // ================================================================

  /**
   * Retrieve relevant lessons/procedures before running an agent task
   * 
   * @example
   * ```typescript
   * const memory = await mnemonic.recall({
   *   agentId: 'agent-123',
   *   task: 'Deploy FastAPI to Railway',
   *   limit: 5
   * });
   * ```
   */
  async recall(request: RecallRequest): Promise<RecallResponse> {
    return this.request<RecallResponse>('POST', '/v1/recall', {
      agent_id: request.agentId,
      task: request.task,
      limit: request.limit || 5,
      min_confidence: request.minConfidence || 0.6,
      as_prompt: request.asPrompt || false,
    });
  }

  /**
   * Capture an agent execution. Returns immediately; reflection runs asynchronously.
   * 
   * @example
   * ```typescript
   * await mnemonic.capture({
   *   agentId: 'agent-123',
   *   task: 'Deploy FastAPI to Railway',
   *   actions: [
   *     { type: 'create_file', target: 'railway.json', result: 'success' }
   *   ],
   *   output: 'Deployed successfully',
   *   success: true
   * });
   * ```
   */
  async capture(request: CaptureRequest): Promise<CaptureResponse> {
    return this.request<CaptureResponse>('POST', '/v1/events', {
      agent_id: request.agentId,
      task: request.task,
      actions: request.actions,
      output: request.output,
      success: request.success,
      time_taken: request.timeTaken,
      retries: request.retries || 0,
      metadata: request.metadata || {},
    });
  }

  // ================================================================
  // AGENT MANAGEMENT
  // ================================================================

  /**
   * Create a new agent
   * 
   * @example
   * ```typescript
   * const agent = await mnemonic.createAgent({
   *   externalId: 'my-agent-1',
   *   name: 'Production Agent',
   *   description: 'Main production agent'
   * });
   * ```
   */
  async createAgent(request: CreateAgentRequest): Promise<Agent> {
    return this.request<Agent>('POST', '/v1/agents', {
      external_id: request.externalId,
      name: request.name,
      description: request.description,
      metadata: request.metadata || {},
    });
  }

  /**
   * List all agents for current tenant
   */
  async listAgents(): Promise<Agent[]> {
    return this.request<Agent[]>('GET', '/v1/agents');
  }

  /**
   * Get agent statistics
   */
  async getAgentStats(agentId: string): Promise<AgentStats> {
    return this.request<AgentStats>('GET', `/v1/agents/${agentId}/stats`);
  }

  // ================================================================
  // LESSONS & PROCEDURES
  // ================================================================

  /**
   * List lessons
   */
  async listLessons(agentId?: string, limit: number = 50): Promise<Lesson[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (agentId) {
      params.set('agent_id', agentId);
    }
    return this.request<Lesson[]>('GET', `/v1/lessons?${params}`);
  }

  /**
   * List procedures
   */
  async listProcedures(agentId?: string): Promise<Procedure[]> {
    const params = agentId ? `?agent_id=${agentId}` : '';
    return this.request<Procedure[]>('GET', `/v1/procedures${params}`);
  }

  /**
   * Submit feedback on a lesson or procedure
   */
  async submitFeedback(request: FeedbackRequest): Promise<{ status: string }> {
    return this.request('POST', '/v1/feedback', {
      lesson_id: request.lessonId,
      procedure_id: request.procedureId,
      rating: request.rating,
      comment: request.comment,
    });
  }

  // ================================================================
  // v2 NETWORK EFFECTS
  // ================================================================

  /**
   * Report how using a lesson affected task outcome
   * 
   * Enables network effect tracking:
   * - Which lessons are most helpful
   * - Success rates across different contexts
   * - Attribution (which agents create valuable lessons)
   * 
   * @example
   * ```typescript
   * await mnemonic.reportLessonEffectiveness({
   *   lessonId: 'lesson-uuid',
   *   agentId: 'agent-123',
   *   task: 'Deploy to Railway',
   *   outcome: 'success',
   *   improvementMetrics: {
   *     timeSavedMs: 1800000,
   *     retriesReduced: 2
   *   }
   * });
   * ```
   */
  async reportLessonEffectiveness(
    request: LessonEffectivenessReport
  ): Promise<LessonEffectivenessResponse> {
    return this.request<LessonEffectivenessResponse>(
      'POST',
      '/v1/analytics/lesson-effectiveness',
      {
        lesson_id: request.lessonId,
        agent_id: request.agentId,
        task: request.task,
        outcome: request.outcome,
        improvement_metrics: request.improvementMetrics || {},
      }
    );
  }

  /**
   * Get detailed analytics for a specific lesson
   * 
   * @example
   * ```typescript
   * const analytics = await mnemonic.getLessonAnalytics('lesson-uuid');
   * console.log(`Quality: ${analytics.qualityScore}`);
   * console.log(`Success rate: ${analytics.successRate}`);
   * ```
   */
  async getLessonAnalytics(lessonId: string): Promise<LessonAnalytics> {
    return this.request<LessonAnalytics>(
      'GET',
      `/v1/analytics/lesson/${lessonId}`
    );
  }

  /**
   * Get global network effects statistics
   * 
   * Shows how the global knowledge network is performing:
   * - Total lessons in the system
   * - Public vs private distribution
   * - Top performing lessons
   * - Cross-tenant learning metrics
   * 
   * @example
   * ```typescript
   * const stats = await mnemonic.getNetworkEffectsStats();
   * console.log(`Total lessons: ${stats.totalLessons}`);
   * console.log(`Cross-tenant learnings: ${stats.crossTenantLearningEvents}`);
   * console.log(`Top lesson: ${stats.topLessons[0].content}`);
   * ```
   */
  async getNetworkEffectsStats(): Promise<NetworkEffectsStats> {
    return this.request<NetworkEffectsStats>(
      'GET',
      '/v1/analytics/network-effects'
    );
  }
}

// Default export
export default Mnemonic;
