import axios from 'axios';

const API_BASE_URL = 'http://localhost:8012/api';

export interface StandardInfo {
    code: string;
    name: string | null;
    year: string | null;
}

export interface SearchResult {
    code: string;
    name: string;
    status: string;
    url: string;
    source?: 'excel' | 'db' | 'online';
    soujianzhu_url?: string;
}

export interface StandardDetail {
    department: string;
    release_date: string;
    implement_date: string;
    status: string;
    englishName?: string;
    ics?: string;
    publisher?: string;
    pages?: string;
    drafting_unit: string;
    replaced_by: string;
    replaces: string;
    url?: string;
    technical_committee?: string;
    ccs?: string;
    obsolete_date?: string;
    replaced_by_code?: string;
    replaced_by_name?: string;
}

export const api = {
    extractStandards: async (text: string): Promise<StandardInfo[]> => {
        const response = await axios.post(`${API_BASE_URL}/extract`, { text });
        return response.data.standards;
    },

    searchStandard: async (keyword: string): Promise<SearchResult[]> => {
        const response = await axios.post(`${API_BASE_URL}/search`, { keyword });
        return response.data.results;
    },

    getStandardDetail: async (url?: string, code?: string): Promise<StandardDetail> => {
        const response = await axios.post(`${API_BASE_URL}/detail`, { url, code });
        return response.data;
    },

    getDatabaseStats: async (): Promise<{ count: number; last_updated: string }> => {
        const response = await axios.get(`${API_BASE_URL}/stats`);
        return response.data;
    },

    getCsresRedirectUrl: async (keyword: string): Promise<string> => {
        const response = await axios.get(`${API_BASE_URL}/redirect_csres`, { params: { keyword } });
        return response.data.url;
    }
};
