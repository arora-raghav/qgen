/**
 * QGen Q&A Quality Analysis Utilities
 * Copied directly from qelab-ui/client/src/lib/qaQualityAnalysis.ts
 */

export interface QARecord {
  question: string;
  answer: string;
  context?: string;
  difficulty?: string;
  topic?: string;
  question_type?: string;
  explanation?: string;
  keywords?: string;
  [key: string]: any;
}

export interface QualityScore {
  overall_score: number;
  breakdown: {
    completeness: number;
    structure: number;
    grounding: number;
    coverage: number;
  };
  issues: Array<{
    type: string;
    count: number;
    severity: 'low' | 'medium' | 'high';
    description: string;
  }>;
}

export interface QualityComments {
  high_quality_records: number;
  records_needing_attention: Array<{
    issue_type: string;
    count: number;
    recommendation: string;
  }>;
  overall_assessment: string;
}

export interface SchemaCoverage {
  fields_utilized: number;
  total_schema_fields: number;
  coverage_percentage: number;
  utilized_fields: string[];
  unused_fields: string[];
}

export interface GroundingMetrics {
  avg_grounding_score: number;
  well_grounded_pairs: number;
  grounding_distribution: {
    high: number;
    medium: number;
    low: number;
  };
}

export interface QAQualityMetrics {
  total_records: number;
  total_qa_pairs: number;
  quality_score: QualityScore;
  schema_coverage: SchemaCoverage;
  grounding_metrics: GroundingMetrics;
  content_metrics: {
    question_length_stats: { min: number; max: number; avg: number };
    answer_length_stats: { min: number; max: number; avg: number };
    context_utilization: number;
    answer_question_ratio: number;
    questions_with_keywords: number;
    answers_with_explanations: number;
  };
  difficulty_distribution: { [key: string]: number };
  question_type_distribution: { [key: string]: number };
  topic_coverage: {
    unique_topics: number;
    topic_distribution: { [topic: string]: number };
  };
  quality_comments: QualityComments;
}

const REQUIRED_FIELDS = ['question', 'answer', 'context', 'difficulty', 'topic', 'question_type'];
const OPTIONAL_FIELDS = ['explanation', 'keywords'];
const VALID_DIFFICULTY = ['basic', 'intermediate', 'advanced'];
const VALID_QUESTION_TYPES = ['theoretical', 'practical', 'code', 'application'];

export function calculateQAQualityMetrics(records: QARecord[]): QAQualityMetrics {
  if (!records || records.length === 0) return getEmptyMetrics();

  const totalRecords = records.length;
  const completeness = calculateCompleteness(records);
  const structure = calculateStructureQuality(records);
  const grounding = calculateGroundingMetrics(records);
  const schemaCoverage = calculateSchemaCoverage(records);
  const qualityScore = calculateQualityScore(completeness, structure, grounding.avg_grounding_score, schemaCoverage.coverage_percentage, records);
  const qualityComments = generateQualityComments(records, qualityScore);
  const difficultyDistribution = calculateDifficultyDistribution(records);
  const questionTypeDistribution = calculateQuestionTypeDistribution(records);
  const topicCoverage = calculateTopicCoverage(records);
  const contentMetrics = calculateContentMetrics(records);

  return {
    total_records: totalRecords,
    total_qa_pairs: totalRecords,
    quality_score: qualityScore,
    schema_coverage: schemaCoverage,
    grounding_metrics: grounding,
    content_metrics: contentMetrics,
    difficulty_distribution: difficultyDistribution,
    question_type_distribution: questionTypeDistribution,
    topic_coverage: topicCoverage,
    quality_comments: qualityComments
  };
}

function calculateCompleteness(records: QARecord[]): number {
  if (records.length === 0) return 0;
  let totalFields = 0, filledFields = 0;
  records.forEach(record => {
    REQUIRED_FIELDS.forEach(field => {
      totalFields++;
      if (record[field] && String(record[field]).trim().length > 0) filledFields++;
    });
  });
  return totalFields > 0 ? Math.round((filledFields / totalFields) * 100) : 0;
}

function calculateStructureQuality(records: QARecord[]): number {
  if (records.length === 0) return 0;
  let validRecords = 0;
  records.forEach(record => {
    let isValid = true;
    REQUIRED_FIELDS.forEach(field => {
      if (!record[field] || String(record[field]).trim().length === 0) isValid = false;
    });
    if (record.difficulty && !VALID_DIFFICULTY.includes(record.difficulty)) isValid = false;
    if (record.question_type && !VALID_QUESTION_TYPES.includes(record.question_type)) isValid = false;
    if (isValid) validRecords++;
  });
  return Math.round((validRecords / records.length) * 100);
}

function calculateSchemaCoverage(records: QARecord[]): SchemaCoverage {
  const allFields = [...REQUIRED_FIELDS, ...OPTIONAL_FIELDS];
  const utilizedFields: string[] = [];
  const unusedFields: string[] = [];
  allFields.forEach(field => {
    const isUsed = records.some(record => record[field] && String(record[field]).trim().length > 0);
    if (isUsed) utilizedFields.push(field);
    else unusedFields.push(field);
  });
  const coveragePercentage = allFields.length > 0 ? Math.round((utilizedFields.length / allFields.length) * 100) : 0;
  return { fields_utilized: utilizedFields.length, total_schema_fields: allFields.length, coverage_percentage: coveragePercentage, utilized_fields: utilizedFields, unused_fields: unusedFields };
}

function calculateGroundingMetrics(records: QARecord[]): GroundingMetrics {
  if (records.length === 0) return { avg_grounding_score: 0, well_grounded_pairs: 0, grounding_distribution: { high: 0, medium: 0, low: 0 } };
  let totalGroundingScore = 0, wellGroundedPairs = 0;
  const distribution = { high: 0, medium: 0, low: 0 };
  records.forEach(record => {
    let groundingScore = 0;
    const contextLength = record.context ? record.context.length : 0;
    const answerLength = record.answer ? record.answer.length : 0;
    if (contextLength > 0 && answerLength > 0) groundingScore += Math.min(100, (contextLength / 100) * 100) * 0.4;
    const questionLength = record.question ? record.question.length : 0;
    if (questionLength > 0 && answerLength > 0) groundingScore += Math.min(100, (answerLength / questionLength) * 20) * 0.3;
    let qualityScore = 0;
    if (record.explanation && record.explanation.trim().length > 0) qualityScore += 50;
    if (record.keywords && record.keywords.trim().length > 0) qualityScore += 30;
    if (answerLength > 50) qualityScore += 20;
    groundingScore += Math.min(100, qualityScore) * 0.3;
    groundingScore = Math.min(100, groundingScore);
    totalGroundingScore += groundingScore;
    if (groundingScore >= 70) wellGroundedPairs++;
    if (groundingScore >= 80) distribution.high++;
    else if (groundingScore >= 60) distribution.medium++;
    else distribution.low++;
  });
  return { avg_grounding_score: Math.round(totalGroundingScore / records.length), well_grounded_pairs: wellGroundedPairs, grounding_distribution: distribution };
}

function calculateQualityScore(completeness: number, structure: number, grounding: number, coverage: number, records: QARecord[]): QualityScore {
  const overallScore = Math.round((completeness * 0.25) + (structure * 0.25) + (grounding * 0.25) + (coverage * 0.25));
  const issues = identifyQualityIssues(records, completeness, structure, grounding, coverage);
  return { overall_score: Math.min(100, Math.max(0, overallScore)), breakdown: { completeness, structure, grounding, coverage }, issues };
}

function identifyQualityIssues(records: QARecord[], completeness: number, structure: number, grounding: number, coverage: number) {
  const issues: Array<{ type: string; count: number; severity: 'low' | 'medium' | 'high'; description: string }> = [];
  if (completeness < 95) issues.push({ type: 'incomplete_fields', count: Math.round(records.length * (100 - completeness) / 100), severity: completeness < 80 ? 'high' : completeness < 90 ? 'medium' : 'low', description: `${100 - completeness}% of required fields are missing or empty` });
  if (structure < 95) issues.push({ type: 'format_issues', count: Math.round(records.length * (100 - structure) / 100), severity: structure < 80 ? 'high' : structure < 90 ? 'medium' : 'low', description: `${100 - structure}% of records have formatting or validation issues` });
  if (grounding < 70) issues.push({ type: 'poor_grounding', count: Math.round(records.length * (100 - grounding) / 100), severity: grounding < 50 ? 'high' : 'medium', description: `${100 - grounding}% of answers are not well-grounded in source context` });
  if (coverage < 80) issues.push({ type: 'low_schema_coverage', count: records.length, severity: coverage < 60 ? 'high' : 'medium', description: `Only ${coverage}% of schema fields are being utilized` });
  return issues;
}

function generateQualityComments(records: QARecord[], qualityScore: QualityScore): QualityComments {
  const highQualityRecords = Math.round(records.length * (qualityScore.overall_score / 100));
  const recommendations: Record<string, string> = {
    incomplete_fields: 'Consider regenerating records with missing fields or manually filling gaps',
    format_issues: 'Review and fix formatting issues, especially difficulty levels and question types',
    poor_grounding: 'Improve answer quality by ensuring answers are well-grounded in source context',
    low_schema_coverage: 'Utilize more schema fields to improve dataset richness and coverage'
  };
  return {
    high_quality_records: highQualityRecords,
    records_needing_attention: qualityScore.issues.map(issue => ({ issue_type: issue.type, count: issue.count, recommendation: recommendations[issue.type] || 'Review and improve dataset quality' })),
    overall_assessment: generateOverallAssessment(qualityScore.overall_score, records.length)
  };
}

function generateOverallAssessment(score: number, totalRecords: number): string {
  if (score >= 90) return `Excellent! Your dataset of ${totalRecords} Q&A pairs is of outstanding quality and ready for training.`;
  if (score >= 80) return `Great! Your dataset of ${totalRecords} Q&A pairs is of high quality with minor areas for improvement.`;
  if (score >= 70) return `Good! Your dataset of ${totalRecords} Q&A pairs is solid but could benefit from some refinements.`;
  if (score >= 60) return `Your dataset of ${totalRecords} Q&A pairs has potential but needs attention to improve quality.`;
  return `Your dataset of ${totalRecords} Q&A pairs requires significant improvements before training use.`;
}

function calculateDifficultyDistribution(records: QARecord[]) {
  const distribution: Record<string, number> = { basic: 0, intermediate: 0, advanced: 0 };
  records.forEach(record => { if (record.difficulty && VALID_DIFFICULTY.includes(record.difficulty)) distribution[record.difficulty]++; });
  return distribution;
}

function calculateQuestionTypeDistribution(records: QARecord[]) {
  const distribution: Record<string, number> = { theoretical: 0, practical: 0, code: 0, application: 0 };
  records.forEach(record => { if (record.question_type && VALID_QUESTION_TYPES.includes(record.question_type)) distribution[record.question_type]++; });
  return distribution;
}

function calculateTopicCoverage(records: QARecord[]) {
  const topicMap = new Map<string, number>();
  records.forEach(record => { if (record.topic?.trim()) { const t = record.topic.trim().toLowerCase(); topicMap.set(t, (topicMap.get(t) || 0) + 1); } });
  return { unique_topics: topicMap.size, topic_distribution: Object.fromEntries(topicMap) };
}

function calculateContentMetrics(records: QARecord[]) {
  const qLengths = records.map(r => r.question?.length || 0).filter(l => l > 0);
  const aLengths = records.map(r => r.answer?.length || 0).filter(l => l > 0);
  const questionsWithKeywords = records.filter(r => r.keywords?.trim()).length;
  const answersWithExplanations = records.filter(r => r.explanation?.trim()).length;
  const contextUtilization = Math.round((records.filter(r => r.context?.trim()).length / records.length) * 100);
  let totalRatio = 0, validRatios = 0;
  records.forEach(r => { const q = r.question?.length || 0, a = r.answer?.length || 0; if (q > 0 && a > 0) { totalRatio += a / q; validRatios++; } });
  return {
    question_length_stats: { min: qLengths.length ? Math.min(...qLengths) : 0, max: qLengths.length ? Math.max(...qLengths) : 0, avg: qLengths.length ? Math.round(qLengths.reduce((a, b) => a + b, 0) / qLengths.length) : 0 },
    answer_length_stats: { min: aLengths.length ? Math.min(...aLengths) : 0, max: aLengths.length ? Math.max(...aLengths) : 0, avg: aLengths.length ? Math.round(aLengths.reduce((a, b) => a + b, 0) / aLengths.length) : 0 },
    context_utilization: contextUtilization,
    answer_question_ratio: validRatios > 0 ? Math.round(totalRatio / validRatios * 100) / 100 : 0,
    questions_with_keywords: questionsWithKeywords,
    answers_with_explanations: answersWithExplanations
  };
}

function getEmptyMetrics(): QAQualityMetrics {
  return {
    total_records: 0, total_qa_pairs: 0,
    quality_score: { overall_score: 0, breakdown: { completeness: 0, structure: 0, grounding: 0, coverage: 0 }, issues: [] },
    schema_coverage: { fields_utilized: 0, total_schema_fields: 0, coverage_percentage: 0, utilized_fields: [], unused_fields: [] },
    grounding_metrics: { avg_grounding_score: 0, well_grounded_pairs: 0, grounding_distribution: { high: 0, medium: 0, low: 0 } },
    content_metrics: { question_length_stats: { min: 0, max: 0, avg: 0 }, answer_length_stats: { min: 0, max: 0, avg: 0 }, context_utilization: 0, answer_question_ratio: 0, questions_with_keywords: 0, answers_with_explanations: 0 },
    difficulty_distribution: { basic: 0, intermediate: 0, advanced: 0 },
    question_type_distribution: { theoretical: 0, practical: 0, code: 0, application: 0 },
    topic_coverage: { unique_topics: 0, topic_distribution: {} },
    quality_comments: { high_quality_records: 0, records_needing_attention: [], overall_assessment: 'No data available for quality analysis' }
  };
}
