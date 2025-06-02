export interface LogEntry {
    timestamp: string;
    level: string;
    name: string;
    message: string;
    extra_metadata?: Record<string, unknown>;
}

export interface Filters {
    level?: string;
    name?: string;
    startTime?: Date;
    endTime?: Date;
} 