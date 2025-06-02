export interface LogEntry {
    id: number;
    timestamp: string;  // ISO datetime string
    name: string;
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    pathname?: string;
    lineno?: number;
    msg: string;
    args?: unknown;  // JSON data
    exc_info?: string;
    func?: string;
    extra_metadata?: unknown;  // JSON data
    
    [key: string]: unknown;  // Keep the index signature for any additional fields
}
