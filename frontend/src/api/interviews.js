import apiClient from './client';

export const interviewsApi = {
  getUserSessions: async () => {
    const res = await apiClient.get('/interviews');
    return res.data;
  },

  createInterview: async (resumeId, jdId, totalQuestions = 8, difficultyPreference = 'ADAPTIVE') => {
    const res = await apiClient.post('/interviews', {
      resume_id: resumeId,
      jd_id: jdId,
      total_questions: totalQuestions,
      difficulty_preference: difficultyPreference
    });
    return res.data;
  },

  saveSession: async (sessionId) => {
    const res = await apiClient.post(`/interviews/${sessionId}/save`);
    return res.data;
  },

  unsaveSession: async (sessionId) => {
    const res = await apiClient.post(`/interviews/${sessionId}/unsave`);
    return res.data;
  },

  getInterview: async (sessionId) => {
    const res = await apiClient.get(`/interviews/${sessionId}`);
    return res.data;
  },

  deleteSession: async (sessionId) => {
    const res = await apiClient.delete(`/interviews/${sessionId}`);
    return res.data;
  },

  submitAnswer: async (sessionId, sessionQuestionId, answerText, timeTakenSeconds = 0) => {
    const res = await apiClient.post(`/interviews/${sessionId}/answers`, {
      session_question_id: sessionQuestionId,
      answer_text: answerText,
      time_taken_seconds: timeTakenSeconds
    });
    return res.data;
  }
};
