export interface LogEntry {
    timestamp: string;
    level: string;
    name: string;
    message: string;
}

export interface Filters {
    level?: string;
    name?: string;
    startTime?: Date;
    endTime?: Date;
} 