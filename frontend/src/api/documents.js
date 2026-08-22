import apiClient from './client';

export const documentsApi = {
  uploadResume: async (formData) => {
    const res = await apiClient.post('/resumes', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  getResume: async (id) => {
    const res = await apiClient.get(`/resumes/${id}`);
    return res.data;
  },
  listResumes: async () => {
    const res = await apiClient.get('/resumes');
    return res.data;
  },
  createJobDescription: async (title, company, text) => {
    const res = await apiClient.post('/job-descriptions', { title, company, text });
    return res.data;
  },
  getJobDescription: async (id) => {
    const res = await apiClient.get(`/job-descriptions/${id}`);
    return res.data;
  },
  listJobDescriptions: async () => {
    const res = await apiClient.get('/job-descriptions');
    return res.data;
  }
};
