import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { analysisApi } from '../api/analysis';
import { interviewsApi } from '../api/interviews';
import { SkillBadge } from '../components/SkillBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { 
  CheckCircle2, AlertCircle, Award, Sparkles, ArrowLeft, 
  Send, ChevronDown, ChevronUp, Check, Bookmark, BookmarkCheck
} from 'lucide-react';

export const AnalysisPage = () => {
  const { resumeId, jdId } = useParams();
  const [searchParams] = useSearchParams();
  const sessionIdParam = searchParams.get('sessionId');
  const countParam = parseInt(searchParams.get('count') || '8', 10);

  // States
  const [analysisData, setAnalysisData] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [sessionId, setSessionId] = useState(sessionIdParam || null);
  const [isSaved, setIsSaved] = useState(false);
  const [savingLoading, setSavingLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Category Filter
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  // Answers & Evaluations state for each question
  const [answersState, setAnswersState] = useState({});
  const [expandedQuestions, setExpandedQuestions] = useState({});

  useEffect(() => {
    loadSessionAndAnalysis();
  }, [resumeId, jdId, sessionIdParam]);

  const loadSessionAndAnalysis = async () => {
    try {
      setLoading(true);
      setError('');

      // 1. Fetch Skill Gap & Role Analysis
      const gapRes = await analysisApi.analyzeResumeAndJD(resumeId, jdId);
      setAnalysisData(gapRes);

      // 2. Fetch Existing Session or Create Fresh Session
      let currentSession;
      if (sessionIdParam) {
        currentSession = await interviewsApi.getInterview(sessionIdParam);
      } else {
        currentSession = await interviewsApi.createInterview(resumeId, jdId, countParam, 'ADAPTIVE');
      }

      setSessionId(currentSession.id);
      setSessionData(currentSession);
      setIsSaved(Boolean(currentSession.is_saved));
      setQuestions(currentSession.questions || []);

      // Pre-fill any previously saved answers & evaluations (start collapsed)
      const initialAnswers = {};
      const initialExpanded = {};

      currentSession.questions?.forEach((q) => {
        if (q.is_answered) {
          initialAnswers[q.session_question_id] = {
            answerText: q.answer_text || '',
            evaluating: false,
            result: {
              score: q.score,
              feedback: q.feedback,
              strengths: q.strengths,
              areas_for_improvement: q.areas_for_improvement,
              evaluator_type: q.source_type || 'TWO_STAGE_EVAL'
            }
          };
        }
      });

      setAnswersState(initialAnswers);
      setExpandedQuestions(initialExpanded);

    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load session and questions.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSave = async () => {
    if (!sessionId) return;
    try {
      setSavingLoading(true);
      if (!isSaved) {
        await interviewsApi.saveSession(sessionId);
        setIsSaved(true);
      } else {
        await interviewsApi.unsaveSession(sessionId);
        setIsSaved(false);
      }
    } catch (err) {
      console.error('Failed to toggle save session:', err);
    } finally {
      setSavingLoading(false);
    }
  };

  const toggleExpand = (qId) => {
    setExpandedQuestions(prev => ({
      ...prev,
      [qId]: !prev[qId]
    }));
  };

  const handleAnswerChange = (qId, text) => {
    setAnswersState(prev => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || {}),
        answerText: text,
        error: ''
      }
    }));
  };

  const handleEvaluateAnswer = async (q) => {
    const qId = q.session_question_id;
    const state = answersState[qId] || {};
    const answerText = state.answerText || '';

    if (!answerText.trim()) {
      setAnswersState(prev => ({
        ...prev,
        [qId]: { ...(prev[qId] || {}), error: 'Please enter an answer to evaluate.' }
      }));
      return;
    }

    try {
      setAnswersState(prev => ({
        ...prev,
        [qId]: { ...(prev[qId] || {}), evaluating: true, error: '' }
      }));

      // Submit and evaluate answer
      const res = await interviewsApi.submitAnswer(
        sessionId,
        qId,
        answerText,
        0
      );

      setAnswersState(prev => ({
        ...prev,
        [qId]: {
          ...(prev[qId] || {}),
          evaluating: false,
          result: res
        }
      }));
    } catch (err) {
      console.error(err);
      setAnswersState(prev => ({
        ...prev,
        [qId]: {
          ...(prev[qId] || {}),
          evaluating: false,
          error: err.response?.data?.detail || 'Failed to evaluate answer. Please try again.'
        }
      }));
    }
  };

  if (loading) {
    return (
      <div style={{ maxWidth: '600px', margin: '80px auto', textAlign: 'center' }}>
        <LoadingSpinner size="lg" />
        <h3 style={{ marginTop: '16px', fontSize: '18px', fontWeight: '700' }}>
          Loading Question Set & Skill Analysis
        </h3>
        <p style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>
          Retrieving grounded questions and taxonomy breakdown...
        </p>
      </div>
    );
  }

  if (error || !analysisData) {
    return (
      <div style={{ maxWidth: '500px', margin: '60px auto', textAlign: 'center' }}>
        <div className="card" style={{ padding: '24px' }}>
          <AlertCircle size={36} color="#e11d48" style={{ margin: '0 auto 8px' }} />
          <h2 style={{ fontSize: '16px', fontWeight: '700' }}>Analysis Error</h2>
          <p style={{ fontSize: '12px', color: '#475569', margin: '8px 0 16px' }}>{error || 'Unable to load session.'}</p>
          <Link to="/dashboard" className="btn-primary" style={{ margin: '0 auto' }}>
            <ArrowLeft size={14} /> Back
          </Link>
        </div>
      </div>
    );
  }

  const { skill_gap, role_analysis, summary } = analysisData;
  const matchPct = Math.round(skill_gap.match_percentage || 0);

  // Filter questions
  const filteredQuestions = selectedCategory === 'ALL'
    ? questions
    : questions.filter(q => q.category === selectedCategory);

  const categories = ['ALL', ...new Set(questions.map(q => q.category))];

  return (
    <div className="analysis-page">
      
      {/* Top Header Card */}
      <section className="analysis-header-card">
        <div>
          <Link to="/dashboard" className="back-link">
            <ArrowLeft size={14} /> Back
          </Link>
          
          <div className="header-meta">
            <span className="company-tag">{sessionData?.company || 'Target Company'}</span>
            <span>•</span>
            <span>{role_analysis.inferred_role_family} ({role_analysis.inferred_seniority})</span>
          </div>

          <h1 className="header-title">
            {sessionData?.role_title || role_analysis.inferred_role_family}
          </h1>
        </div>

        {/* Right Header Actions */}
        <div className="header-right-actions">
          
          {/* Explicit Save Session Button */}
          <button
            type="button"
            onClick={handleToggleSave}
            disabled={savingLoading}
            className={`btn-save-session ${isSaved ? 'saved' : 'not-saved'}`}
          >
            {isSaved ? (
              <>
                <BookmarkCheck size={16} />
                <span>Saved to Sessions</span>
              </>
            ) : (
              <>
                <Bookmark size={16} />
                <span>Save Session</span>
              </>
            )}
          </button>

          {/* Match Score Badge */}
          <div className="alignment-score-pill">
            <div className="label">Alignment</div>
            <div className="score">{matchPct}%</div>
          </div>

        </div>
      </section>

      {/* Skill Gap Breakdown Card */}
      <section className="skill-breakdown-card">
        <div>
          <h2 style={{ fontSize: '14px', fontWeight: '700' }}>O*NET Skill Taxonomy Breakdown</h2>
          <p style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{summary}</p>
        </div>

        <div className="skill-columns-grid">
          
          {/* Matched Skills */}
          <div className="skill-column matched">
            <div className="column-title">
              <CheckCircle2 size={14} />
              <h3>Matched Skills ({skill_gap.matched_skills.length})</h3>
            </div>
            <div className="skills-wrap">
              {skill_gap.matched_skills.length > 0 ? (
                skill_gap.matched_skills.map((s, i) => (
                  <SkillBadge key={i} skill={s} type="matched" />
                ))
              ) : (
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>No overlapping skills detected.</span>
              )}
            </div>
          </div>

          {/* Missing JD Requirements */}
          <div className="skill-column missing">
            <div className="column-title">
              <AlertCircle size={14} />
              <h3>Target Skill Gaps ({skill_gap.missing_jd_skills.length})</h3>
            </div>
            <div className="skills-wrap">
              {skill_gap.missing_jd_skills.length > 0 ? (
                skill_gap.missing_jd_skills.map((s, i) => (
                  <SkillBadge key={i} skill={s} type="missing" />
                ))
              ) : (
                <span style={{ fontSize: '11px', color: '#059669', fontWeight: '600' }}>Full requirements covered!</span>
              )}
            </div>
          </div>

          {/* Resume Only Strengths */}
          <div className="skill-column strengths">
            <div className="column-title">
              <Award size={14} />
              <h3>Resume Strengths ({skill_gap.resume_only_skills.length})</h3>
            </div>
            <div className="skills-wrap">
              {skill_gap.resume_only_skills.length > 0 ? (
                skill_gap.resume_only_skills.map((s, i) => (
                  <SkillBadge key={i} skill={s} type="resume_only" />
                ))
              ) : (
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>None</span>
              )}
            </div>
          </div>

        </div>
      </section>

      {/* Generated Questions List Section */}
      <section className="questions-section">
        
        {/* Filter Bar */}
        <div className="questions-filter-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="#4f46e5" />
            <h2 style={{ fontSize: '16px', fontWeight: '700' }}>
              Questions ({filteredQuestions.length})
            </h2>
          </div>

          {/* Category Filter Pills */}
          <div className="filter-category-pills">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`filter-pill ${selectedCategory === cat ? 'active' : ''}`}
              >
                {cat.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Question Cards List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredQuestions.map((q) => {
            const qId = q.session_question_id;
            const isExpanded = !!expandedQuestions[qId];
            const ansState = answersState[qId] || {};
            const result = ansState.result;

            return (
              <div key={qId} className="question-card">
                {/* Clickable Header */}
                <div onClick={() => toggleExpand(qId)} className="question-header">
                  <div style={{ flex: 1 }}>
                    <div className="question-tags-row">
                      <span className="q-badge">Q{q.position}</span>
                      <span className="q-category-badge">{q.category}</span>
                      {q.target_skill && (
                        <span className="q-target-badge">Target: {q.target_skill}</span>
                      )}
                      {result?.score != null && (
                        <span className="q-score-badge">Score: {result.score}/100</span>
                      )}
                    </div>

                    <div className="question-text">{q.question_text}</div>

                    {q.selection_rationale && (
                      <div className="question-rationale">{q.selection_rationale}</div>
                    )}
                  </div>

                  <button style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>

                {/* Expandable Answer Workspace */}
                {isExpanded && (
                  <div className="question-body">
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontSize: '11px', fontWeight: '700', color: '#334155' }}>Candidate Answer</span>
                        <span style={{ fontSize: '11px', color: '#94a3b8' }}>Type response for instant grounded evaluation</span>
                      </div>
                      <textarea
                        value={ansState.answerText || ''}
                        onChange={(e) => handleAnswerChange(qId, e.target.value)}
                        placeholder="Provide your complete answer here with architectural principles or structured examples..."
                        className="answer-textarea"
                      />
                    </div>

                    {ansState.error && (
                      <p style={{ fontSize: '11px', color: '#e11d48', fontWeight: '600' }}>{ansState.error}</p>
                    )}

                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        type="button"
                        onClick={() => handleEvaluateAnswer(q)}
                        disabled={ansState.evaluating}
                        className="btn-primary"
                        style={{ padding: '6px 14px', fontSize: '11px' }}
                      >
                        {ansState.evaluating ? (
                          <>
                            <LoadingSpinner size="sm" />
                            <span>Analyzing...</span>
                          </>
                        ) : (
                          <>
                            <Send size={12} />
                            <span>{result ? 'Re-Analyze Answer' : 'Analyze My Answer'}</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Instant Evaluation Feedback Result */}
                    {result && (
                      <div className="eval-result-card">
                        <div className="eval-header">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: '700' }}>Evaluation Score:</span>
                            <span style={{
                              fontWeight: '800',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: result.score >= 75 ? '#ecfdf5' : result.score >= 50 ? '#fffbeb' : '#fff1f2',
                              color: result.score >= 75 ? '#047857' : result.score >= 50 ? '#b45309' : '#be123c',
                              border: `1px solid ${result.score >= 75 ? '#a7f3d0' : result.score >= 50 ? '#fde68a' : '#fecdd3'}`
                            }}>
                              {result.score} / 100
                            </span>
                          </div>
                          <span style={{ color: '#94a3b8' }}>{result.evaluator_type}</span>
                        </div>

                        <div className="eval-feedback-text">
                          {result.feedback}
                        </div>

                        <div className="eval-details-grid">
                          {result.strengths && (
                            <div className="detail-box strengths">
                              <div style={{ fontWeight: '700', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <Check size={12} /> Strengths
                              </div>
                              <div>{result.strengths}</div>
                            </div>
                          )}
                          {result.areas_for_improvement && (
                            <div className="detail-box improvements">
                              <div style={{ fontWeight: '700', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <Sparkles size={12} /> Improvement Areas
                              </div>
                              <div>{result.areas_for_improvement}</div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

    </div>
  );
};
