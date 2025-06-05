import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { SocketHandler, type InitialLogsResponse, type GetInitialLogsData } from '../components/socket';
import LogTable, { defaultColumns } from '../components/table';
import type { LogEntry } from '../components/log_entry';
import { FilterPanel } from '../components/filter_panel';
import type { DynamicFilters } from '../components/filter_panel';
import { ImportModal } from '../components/import_modal';

const columns = defaultColumns;

export default function HomePage() {
    const [socket] = useState(() => new SocketHandler());
    const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
    const [filters, setFilters] = useState<DynamicFilters>({});
    const [isPaused, setIsPaused] = useState(false);
    const [pendingLogs, setPendingLogs] = useState<LogEntry[]>([]);
    const [showImportModal, setShowImportModal] = useState(false);
    const [recordLimit, setRecordLimit] = useState(1000);
    
    const fetchInitialLogs = useCallback(() => {
        const data: GetInitialLogsData = {
            limit: recordLimit
        };
        
        // Add time filters if they exist
        if (filters.startTime?.value) {
            data.start_time = filters.startTime.value;
        }
        if (filters.endTime?.value) {
            data.end_time = filters.endTime.value;
        }
        
        socket.get_initial_logs(data);
    }, [socket, recordLimit, filters.startTime?.value, filters.endTime?.value]);
    
    const handleImportSuccess = () => {
        setShowImportModal(false);
        fetchInitialLogs();
    };

    const isPausedRef = useRef(isPaused);
    isPausedRef.current = isPaused;

    useEffect(() => {
        // Handle initial logs
        socket.on_initial_logs((initial_logs: InitialLogsResponse) => {
            console.log("Initial logs", initial_logs);
            setLogEntries(initial_logs.logs);
        });

        // Handle new logs
        socket.on_new_log((log: LogEntry) => {
            if (isPausedRef.current) {
                setPendingLogs(prev => [...prev, log]);
            } else {
                setLogEntries(prev => [...prev, log]);
            }
        });

        socket.on_connect(() => {
            fetchInitialLogs();
        });

        // No need for cleanup as the socket handler manages its own connections
    }, [socket]);

    // Debounced effect for date/time filter changes
    const debounceTimeoutRef = useRef<number | undefined>(undefined);
    
    useEffect(() => {
        // Clear existing timeout
        if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
        }
        
        // Set new timeout for date/time changes (debounce for 500ms)
        debounceTimeoutRef.current = window.setTimeout(() => {
            if (socket.is_connected) {
                fetchInitialLogs();
            }
        }, 500);
        
        // Cleanup timeout on unmount
        return () => {
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }
        };
    }, [filters.startTime?.value, filters.endTime?.value, socket.is_connected, fetchInitialLogs]);
    
    // Immediate refresh for record limit changes (no debounce needed)
    useEffect(() => {
        if (socket.is_connected) {
            fetchInitialLogs();
        }
    }, [recordLimit, socket.is_connected, fetchInitialLogs]);

    const togglePause = () => {
        if (isPaused) {
            // Resume: add pending logs to main entries
            setLogEntries(prev => [...prev, ...pendingLogs]);
            setPendingLogs([]);
        }
        setIsPaused(!isPaused);
    };

    // Sort logs by timestamp in descending order (newest first)
    const sortedLogs = useMemo(() => {
        return [...logEntries].sort((a, b) => 
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
    }, [logEntries]);

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="flex items-center justify-between mb-6">
                <h1 className="text-2xl font-bold">Log Viewer</h1>
                <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2">
                        <label htmlFor="record-limit" className="text-sm font-medium text-gray-700">
                            Show:
                        </label>
                        <select
                            id="record-limit"
                            value={recordLimit}
                            onChange={(e) => setRecordLimit(parseInt(e.target.value))}
                            className="rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                        >
                            <option value={100}>100 records</option>
                            <option value={1000}>1,000 records</option>
                            <option value={10000}>10,000 records</option>
                        </select>
                    </div>
                    {pendingLogs.length > 0 && (
                        <span className="text-sm text-gray-600">
                            {pendingLogs.length} pending log{pendingLogs.length !== 1 ? 's' : ''}
                        </span>
                    )}
                    <button
                        onClick={() => setShowImportModal(true)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center space-x-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
                        </svg>
                        <span>Import Logs</span>
                    </button>
                    <button
                        onClick={togglePause}
                        className={`px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                            isPaused 
                                ? 'bg-green-600 hover:bg-green-700 text-white focus:ring-green-500' 
                                : 'bg-yellow-600 hover:bg-yellow-700 text-white focus:ring-yellow-500'
                        }`}
                    >
                        {isPaused ? (
                            <div className="flex items-center space-x-2">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M8 5v14l11-7z"/>
                                </svg>
                                <span>Resume</span>
                            </div>
                        ) : (
                            <div className="flex items-center space-x-2">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                                </svg>
                                <span>Pause</span>
                            </div>
                        )}
                    </button>
                </div>
            </div>
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
            {showImportModal && (
                <ImportModal
                    onClose={() => setShowImportModal(false)}
                    onImportSuccess={handleImportSuccess}
                />
            )}
        </div>
    );
}
