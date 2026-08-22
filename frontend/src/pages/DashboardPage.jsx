import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { documentsApi } from '../api/documents';
import { interviewsApi } from '../api/interviews';
import { 
  Sparkles, Upload, FileText, Briefcase, CheckCircle2, 
  ArrowRight, FolderHeart, Calendar, Trash2, ExternalLink 
} from 'lucide-react';
import { LoadingSpinner } from '../components/LoadingSpinner';

export const DashboardPage = () => {
  const navigate = useNavigate();

  // View Mode: 'generator' | 'saved'
  const [viewMode, setViewMode] = useState('generator');

  // Generator Form States
  const [questionCount, setQuestionCount] = useState(8); // Options: 8, 12, 16, 20
  const [activeTab, setActiveTab] = useState('paste'); // 'upload' | 'paste'
  const [resumeText, setResumeText] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [jdTitle, setJdTitle] = useState('');
  const [jdCompany, setJdCompany] = useState('');
  const [jdText, setJdText] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');

  // Saved Sessions State
  const [savedSessions, setSavedSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    loadSavedSessions();
  }, []);

  const loadSavedSessions = async () => {
    try {
      setLoadingSessions(true);
      const data = await interviewsApi.getUserSessions();
      setSavedSessions(data || []);
    } catch (err) {
      console.error('Failed to load saved sessions:', err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this saved session?')) return;
    try {
      setDeletingId(sessionId);
      await interviewsApi.deleteSession(sessionId);
      setSavedSessions(prev => prev.filter(s => s.id !== sessionId));
    } catch (err) {
      console.error('Failed to delete session:', err);
      alert('Failed to delete session.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleGenerateQuestions = async (e) => {
    e.preventDefault();
    setError('');

    if (activeTab === 'paste' && !resumeText.trim()) {
      setError('Please paste or enter candidate resume text.');
      return;
    }
    if (activeTab === 'upload' && !resumeFile) {
      setError('Please select a resume file (PDF/DOCX).');
      return;
    }
    if (!jdText.trim()) {
      setError('Please provide the target Job Description requirements.');
      return;
    }

    try {
      setLoading(true);
      setLoadingMessage('Parsing resume & extracting skill taxonomy...');

      // 1. Upload / Save Resume
      const resumeFormData = new FormData();
      if (activeTab === 'upload' && resumeFile) {
        resumeFormData.append('file', resumeFile);
      } else {
        resumeFormData.append('raw_text', resumeText);
      }
      const resumeData = await documentsApi.uploadResume(resumeFormData);

      // 2. Save Job Description
      setLoadingMessage('Saving job description requirements...');
      const jdData = await documentsApi.createJobDescription(
        jdTitle || 'Target Role',
        jdCompany || 'Company',
        jdText
      );

      // 3. Generate Grounded Questions
      setLoadingMessage('Retrieving grounded questions from database...');
      const session = await interviewsApi.createInterview(
        resumeData.id,
        jdData.id,
        questionCount,
        'ADAPTIVE'
      );

      // 4. Navigate to Question & Gap Analysis Workspace
      navigate(`/analysis/${resumeData.id}/${jdData.id}?sessionId=${session.id}`);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to process documents. Please check inputs and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenSavedSession = (session) => {
    navigate(`/analysis/${session.resume_id}/${session.jd_id}?sessionId=${session.id}`);
  };

  return (
    <main className="dashboard-page">
      
      {/* Top Banner Bar */}
      <section className="top-banner">
        <div className="banner-title-area">
          <div className="banner-icon-badge">
            <Sparkles size={16} />
          </div>
          <div>
            <h1 className="banner-heading">Interview Question Generator</h1>
            <p className="banner-desc">Grounded O*NET skill matching & RAG question assembly from PostgreSQL</p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <nav className="view-tabs">
          <button
            type="button"
            onClick={() => setViewMode('generator')}
            className={`view-tab-btn ${viewMode === 'generator' ? 'active' : ''}`}
          >
            New Questions
          </button>
          <button
            type="button"
            onClick={() => {
              setViewMode('saved');
              loadSavedSessions();
            }}
            className={`view-tab-btn ${viewMode === 'saved' ? 'active' : ''}`}
          >
            <FolderHeart size={14} color="#7c3aed" />
            <span>Saved Sessions ({savedSessions.length})</span>
          </button>
        </nav>
      </section>

      {error && (
        <div className="alert-error" style={{ margin: '8px 0' }}>
          {error}
        </div>
      )}

      {/* VIEW 1: GENERATOR FORM (Fits neatly without scrolling) */}
      {viewMode === 'generator' && (
        <form onSubmit={handleGenerateQuestions} className="form-container">
          
          <div className="cards-grid">

            {/* Left Card: Resume Input */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <FileText size={16} color="#4f46e5" />
                  <h2>Candidate Resume</h2>
                </div>
                
                <div className="sub-tab-switch">
                  <button
                    type="button"
                    onClick={() => setActiveTab('paste')}
                    className={`sub-tab-btn ${activeTab === 'paste' ? 'active' : ''}`}
                  >
                    Paste Text
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('upload')}
                    className={`sub-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
                  >
                    Upload File
                  </button>
                </div>
              </div>

              {activeTab === 'paste' ? (
                <textarea
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                  placeholder="Paste candidate resume content, summary, experience, and skills..."
                  className="textarea-field"
                />
              ) : (
                <div className="dropzone">
                  <Upload size={24} color="#6366f1" style={{ marginBottom: '6px' }} />
                  <p style={{ fontSize: '12px', fontWeight: '600', color: '#334155' }}>Select PDF or DOCX Resume</p>
                  <input
                    type="file"
                    accept=".pdf,.docx,.doc,.txt"
                    onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                    style={{ fontSize: '11px', marginTop: '8px', cursor: 'pointer' }}
                  />
                  {resumeFile && (
                    <p style={{ fontSize: '11px', color: '#059669', fontWeight: '600', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={12} /> Selected: {resumeFile.name}
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Right Card: Job Description Input */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Briefcase size={16} color="#7c3aed" />
                  <h2>Target Job Description</h2>
                </div>
              </div>

              <div className="jd-inputs-row">
                <div className="input-group">
                  <label className="input-label">Role Title</label>
                  <input
                    type="text"
                    value={jdTitle}
                    onChange={(e) => setJdTitle(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer"
                    className="input-box"
                  />
                </div>
                <div className="input-group">
                  <label className="input-label">Company Name</label>
                  <input
                    type="text"
                    value={jdCompany}
                    onChange={(e) => setJdCompany(e.target.value)}
                    placeholder="e.g. TechCorp Solutions"
                    className="input-box"
                  />
                </div>
              </div>

              <div className="input-group" style={{ flex: 1 }}>
                <label className="input-label">Requirements & Responsibilities</label>
                <textarea
                  value={jdText}
                  onChange={(e) => setJdText(e.target.value)}
                  placeholder="Paste the target job posting, requirements, and responsibilities..."
                  className="textarea-field"
                  style={{ minHeight: '135px' }}
                />
              </div>
            </div>

          </div>

          {/* Bottom Control Bar */}
          <footer className="bottom-control-bar">
            
            {/* 4 Question Count Options: 8, 12, 16, 20 */}
            <div className="question-count-group">
              <span className="count-label">Questions:</span>
              <div className="count-pills">
                {[8, 12, 16, 20].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setQuestionCount(count)}
                    className={`count-btn ${questionCount === count ? 'active' : ''}`}
                  >
                    {count}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Action Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary"
            >
              {loading ? (
                <>
                  <LoadingSpinner size="sm" />
                  <span>{loadingMessage || 'Processing...'}</span>
                </>
              ) : (
                <>
                  <span>Generate Questions & Analyze Gaps</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>

          </footer>

        </form>
      )}

      {/* VIEW 2: SAVED SESSIONS */}
      {viewMode === 'saved' && (
        <section style={{ flex: 1, margin: '8px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <h2 style={{ fontSize: '14px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FolderHeart size={16} color="#4f46e5" />
              <span>Saved Interview Sessions</span>
            </h2>
            <button
              onClick={loadSavedSessions}
              style={{ background: 'none', border: 'none', color: '#4f46e5', fontSize: '11px', fontWeight: '600', cursor: 'pointer', textDecoration: 'underline' }}
            >
              Refresh List
            </button>
          </div>

          {loadingSessions ? (
            <div className="card" style={{ padding: '30px', textAlign: 'center' }}>
              <LoadingSpinner size="md" />
              <p style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>Loading saved sessions...</p>
            </div>
          ) : savedSessions.length === 0 ? (
            <div className="card" style={{ padding: '30px', textAlign: 'center', gap: '8px' }}>
              <FolderHeart size={32} color="#c7d2fe" style={{ margin: '0 auto' }} />
              <h3 style={{ fontSize: '14px', fontWeight: '700' }}>No Saved Sessions Yet</h3>
              <p style={{ fontSize: '11px', color: '#64748b' }}>
                Generate questions and click <strong>Save Session</strong> to preserve them here.
              </p>
              <button
                type="button"
                onClick={() => setViewMode('generator')}
                className="btn-primary"
                style={{ margin: '6px auto 0' }}
              >
                Generate Question Set
              </button>
            </div>
          ) : (
            <div className="saved-sessions-list">
              {savedSessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => handleOpenSavedSession(s)}
                  className="session-card"
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                      <div>
                        <div className="session-company">{s.company || 'Company'}</div>
                        <div className="session-title">{s.role_title}</div>
                      </div>

                      <button
                        onClick={(e) => handleDeleteSession(e, s.id)}
                        disabled={deletingId === s.id}
                        className="btn-icon"
                        title="Delete Session"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    <div className="session-tags">
                      <span className="tag-pill">{s.total_questions} Questions</span>
                      <span className="tag-pill answered">{s.answered_questions}/{s.total_questions} Answered</span>
                      <span className="tag-pill" style={{ background: '#faf5ff', color: '#7c3aed', border: '1px solid #e9d5ff' }}>
                        {s.seniority}
                      </span>
                    </div>
                  </div>

                  <div className="session-footer">
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={12} />
                      {new Date(s.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                    </span>
                    <span style={{ color: '#4f46e5', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Open Session <ExternalLink size={12} />
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

    </main>
  );
};
