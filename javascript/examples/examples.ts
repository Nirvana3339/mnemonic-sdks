/**
 * Mnemonic SDK Usage Examples
 */

import { Mnemonic } from '@mnemonic-ai/sdk';

// ============================================
// Example 1: Basic Usage
// ============================================

async function basicExample() {
  const mnemonic = new Mnemonic({ apiKey: 'mnemo_sk_...' });

  // Create agent
  const agent = await mnemonic.createAgent({
    externalId: 'example-agent',
    name: 'Example Agent'
  });

  // Recall before task
  const memory = await mnemonic.recall({
    agentId: agent.id,
    task: 'Deploy FastAPI to Railway'
  });

  console.log(`Found ${memory.lessons.length} lessons`);

  // Capture after task
  await mnemonic.capture({
    agentId: agent.id,
    task: 'Deploy FastAPI to Railway',
    actions: [{ type: 'deploy', result: 'success' }],
    output: 'Deployed',
    success: true
  });
}

// ============================================
// Example 2: Network Effects Tracking
// ============================================

async function networkEffectsExample() {
  const mnemonic = new Mnemonic({ apiKey: process.env.MNEMO_API_KEY });

  const agent = await mnemonic.createAgent({
    externalId: 'network-agent',
    name: 'Network Effects Agent'
  });

  // 1. Recall lessons
  const memory = await mnemonic.recall({
    agentId: agent.id,
    task: 'Optimize database performance'
  });

  // 2. Show quality scores
  console.log('\n📚 Lessons (sorted by quality):');
  const sorted = memory.lessons
    .sort((a, b) => (b.qualityScore || 0) - (a.qualityScore || 0));

  sorted.forEach(lesson => {
    const quality = lesson.qualityScore || 0.5;
    const emoji = quality > 0.8 ? '🟢' : quality > 0.6 ? '🟡' : '🔴';
    console.log(`${emoji} [${quality.toFixed(2)}] ${lesson.content}`);
    console.log(`   Source: ${lesson.source} | Used ${lesson.usageCount || 0} times`);
  });

  // 3. Execute task
  const success = true;

  // 4. Capture
  await mnemonic.capture({
    agentId: agent.id,
    task: 'Optimize database performance',
    actions: [
      { type: 'analyze', result: 'slow queries identified' },
      { type: 'optimize', result: 'indexes added' }
    ],
    output: 'Performance improved 10x',
    success
  });

  // 5. Report effectiveness
  for (const lesson of memory.lessons) {
    await mnemonic.reportLessonEffectiveness({
      lessonId: lesson.id,
      agentId: agent.id,
      task: 'Optimize database performance',
      outcome: success ? 'success' : 'failure',
      improvementMetrics: {
        timeSavedMs: 3600000,  // 1 hour
        retriesReduced: 3
      }
    });
  }

  // 6. Get analytics
  if (memory.lessons.length > 0) {
    const analytics = await mnemonic.getLessonAnalytics(memory.lessons[0].id);
    console.log(`\n📊 Lesson Analytics:`);
    console.log(`Quality Score: ${analytics.qualityScore.toFixed(2)}`);
    console.log(`Success Rate: ${(analytics.successRate * 100).toFixed(0)}%`);
    console.log(`Usage Count: ${analytics.usageCount}`);
  }

  // 7. Network stats
  const stats = await mnemonic.getNetworkEffectsStats();
  console.log(`\n🌐 Network Effects:`);
  console.log(`Total Lessons: ${stats.totalLessons.toLocaleString()}`);
  console.log(`Cross-Tenant Learnings: ${stats.crossTenantLearningEvents.toLocaleString()}`);
  console.log(`Avg Quality: ${(stats.avgQualityScore * 100).toFixed(0)}%`);
}

// ============================================
// Example 3: Error Handling
// ============================================

async function errorHandlingExample() {
  const mnemonic = new Mnemonic({ apiKey: 'invalid_key' });

  try {
    await mnemonic.recall({
      agentId: 'agent-123',
      task: 'Test task'
    });
  } catch (error) {
    if (error instanceof AuthError) {
      console.error('Authentication failed:', error.message);
    } else if (error instanceof MnemonicError) {
      console.error('API error:', error.message, error.statusCode);
    }
  }
}

// ============================================
// Example 4: React/Next.js Hook
// ============================================

import { useMemo, useEffect, useState } from 'react';

function useMnemonic() {
  return useMemo(
    () => new Mnemonic({ apiKey: process.env.NEXT_PUBLIC_MNEMO_API_KEY }),
    []
  );
}

function NetworkEffectsDashboard() {
  const mnemonic = useMnemonic();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    mnemonic.getNetworkEffectsStats()
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [mnemonic]);

  if (loading) return <div>Loading...</div>;
  if (!stats) return <div>Error loading stats</div>;

  return (
    <div className="dashboard">
      <h1>Network Effects Dashboard</h1>
      <div className="stats">
        <div className="stat">
          <h2>{stats.totalLessons.toLocaleString()}</h2>
          <p>Total Lessons</p>
        </div>
        <div className="stat">
          <h2>{stats.crossTenantLearningEvents.toLocaleString()}</h2>
          <p>Cross-Company Learnings</p>
        </div>
        <div className="stat">
          <h2>{(stats.avgQualityScore * 100).toFixed(0)}%</h2>
          <p>Avg Quality</p>
        </div>
      </div>

      <h2>Top Lessons</h2>
      <ul>
        {stats.topLessons.slice(0, 5).map(lesson => (
          <li key={lesson.lessonId}>
            <strong>[{lesson.qualityScore.toFixed(2)}]</strong> {lesson.content}
            <br />
            <small>Used {lesson.usageCount} times • {(lesson.successRate * 100).toFixed(0)}% success rate</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ============================================
// Run examples
// ============================================

if (require.main === module) {
  console.log('Running Mnemonic SDK examples...\n');
  
  basicExample()
    .then(() => networkEffectsExample())
    .then(() => console.log('\n✅ All examples completed!'))
    .catch(console.error);
}
