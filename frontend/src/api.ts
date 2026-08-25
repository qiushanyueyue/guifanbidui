import axios from 'axios';

const API_BASE_URL = '/api';

export interface StandardInfo {
    code: string;
    name: string | null;
    year: string | null;
    base_code?: string | null;
    normalized_code?: string | null;
    edition?: string | null;
    revision_year?: string | null;
    amendment?: string | null;
}

export type StandardStatus = 'current' | 'upcoming' | 'abolished' | 'replaced' | 'partially_amended' | 'unknown' | 'conflict';
export type VerificationLevel = 'official' | 'cross_verified' | 'single_source' | 'unverified' | 'conflict';

export const STATUS_LABELS: Record<StandardStatus, string> = {
    current: '现行',
    upcoming: '即将实施',
    abolished: '废止',
    replaced: '被替代',
    partially_amended: '局部修订',
    unknown: '待核验',
    conflict: '来源冲突'
};

export const statusLabel = (status: StandardStatus | string | undefined): string => STATUS_LABELS[status as StandardStatus] || '待核验';
export const isInactiveStatus = (status: StandardStatus | string | undefined): boolean => ['abolished', 'replaced'].includes(status || '');

export interface SearchResult {
    id?: number;
    code: string;
    normalized_code?: string | null;
    name: string;
    status: StandardStatus;
    status_label?: string | null;
    url?: string | null;
    source?: string;
    soujianzhu_url?: string | null;
    edition?: string | null;
    revision_year?: string | null;
    amendment?: string | null;
    implement_date?: string | null;
    publish_date?: string | null;
    abolish_date?: string | null;
    replaces?: string | null;
    replaced_by?: string | null;
    article_status?: string | null;
    mandatory_clause_status?: string | null;
    issuing_authority?: string | null;
    canonical_source?: string | null;
    verification_level?: VerificationLevel;
    source_conflict?: boolean;
    last_verified_at?: string | null;
    sources?: SourceInfo[];
}

export interface SourceInfo {
    name: string;
    url?: string | null;
    code?: string | null;
    name_text?: string | null;
    status: StandardStatus;
    raw_status?: string | null;
    fetched_at?: string | null;
    source_updated_at?: string | null;
    parse_status: string;
}

export interface StandardDetail {
    id?: number;
    department: string;
    release_date: string;
    implement_date: string;
    status: StandardStatus;
    status_label?: string | null;
    englishName?: string;
    ics?: string;
    publisher?: string;
    pages?: string;
    drafting_unit: string;
    replaced_by: string | null;
    replaces: string | null;
    article_status?: string | null;
    mandatory_clause_status?: string | null;
    url?: string | null;
    technical_committee?: string;
    ccs?: string;
    obsolete_date?: string;
    replaced_by_code?: string | null;
    replaced_by_name?: string | null;
    edition?: string | null;
    revision_year?: string | null;
    verification_level?: VerificationLevel;
    source_conflict?: boolean;
    last_verified_at?: string | null;
    sources?: SourceInfo[];
}

export interface Stats {
    count: number;
    last_updated: string | null;
    current: number;
    upcoming: number;
    abolished: number;
    replaced: number;
    partially_amended: number;
    unknown: number;
    conflict: number;
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

    getDatabaseStats: async (): Promise<Stats> => {
        const response = await axios.get(`${API_BASE_URL}/stats`);
        return response.data;
    },

    getCsresRedirectUrl: async (keyword: string): Promise<string> => {
        const response = await axios.get(`${API_BASE_URL}/redirect_csres`, { params: { keyword } });
        return response.data.url;
    }
};
