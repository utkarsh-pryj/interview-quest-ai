import apiClient from './client';

export const analysisApi = {
  analyzeResumeAndJD: async (resumeId, jdId) => {
    const res = await apiClient.post(`/analysis/${resumeId}/${jdId}`);
    return res.data;
  }
};
