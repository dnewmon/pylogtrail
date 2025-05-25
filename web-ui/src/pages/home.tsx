import { useEffect, useState, useMemo } from 'react';
import { SocketHandler, type InitialLogsResponse } from '../components/socket';
import LogTable, { defaultColumns } from '../components/table';
import type { LogEntry } from '../components/log_entry';
import { FilterPanel } from '../components/filter_panel';
import type { DynamicFilters } from '../components/filter_panel';

const columns = defaultColumns;

export default function HomePage() {
    const [socket] = useState(() => new SocketHandler());
    const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
    const [filters, setFilters] = useState<DynamicFilters>({});

    useEffect(() => {
        // Handle initial logs
        socket.on_initial_logs((initial_logs: InitialLogsResponse) => {
            console.log("Initial logs", initial_logs);
            setLogEntries(initial_logs.logs);
        });

        // Handle new logs
        socket.on_new_log((log: LogEntry) => {
            setLogEntries(prev => [...prev, log]);
        });

        socket.on_connect(() => {
            socket.get_initial_logs(100);
        });

        // No need for cleanup as the socket handler manages its own connections
    }, [socket]);

    // Sort logs by timestamp in descending order (newest first)
    const sortedLogs = useMemo(() => {
        return [...logEntries].sort((a, b) => 
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );
    }, [logEntries]);

    return (
        <div className="container mx-auto px-4 py-8">
            <h1 className="text-2xl font-bold mb-6">Log Viewer</h1>
            <div className="bg-white rounded-lg shadow">
                <FilterPanel 
                    logEntries={logEntries}
                    onFiltersChange={setFilters}
                />
                <LogTable 
                    logEntries={sortedLogs}
                    columns={columns}
                    filters={filters}
                />
            </div>
        </div>
    );
}
