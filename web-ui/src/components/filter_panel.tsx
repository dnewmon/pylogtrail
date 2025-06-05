import { useState, useEffect } from 'react';
import type { Column } from './table';
import type { LogEntry } from './log_entry';
import { discoverColumns } from './table';

export interface DynamicFilters {
    [key: string]: {
        value: string | null;
        type: 'text' | 'select' | 'date' | 'datetime';
        options?: string[];  // For select type filters
    };
}

interface FilterPanelProps {
    logEntries: LogEntry[];
    onFiltersChange: (filters: DynamicFilters) => void;
}

export function FilterPanel({ logEntries, onFiltersChange }: FilterPanelProps) {
    const [columns, setColumns] = useState<Column[]>([]);
    const [filters, setFilters] = useState<DynamicFilters>({});
    const [, setUniqueValues] = useState<{ [key: string]: Set<string> }>({});
    const [isCollapsed, setIsCollapsed] = useState(true);

    // Discover columns and their unique values
    useEffect(() => {
        const discoveredColumns = discoverColumns(logEntries);
        setColumns(discoveredColumns);

        // Build unique values for each column
        const values: { [key: string]: Set<string> } = {};
        logEntries.forEach(entry => {
            discoveredColumns.forEach(col => {
                const value = entry[col.key];
                if (value !== undefined && value !== null) {
                    if (!values[col.key]) {
                        values[col.key] = new Set();
                    }
                    values[col.key].add(String(value));
                }
            });
            
        });
        setUniqueValues(values);

        // Initialize or update filters, preserving existing values
        setFilters(currentFilters => {
            const updatedFilters: DynamicFilters = {
                startTime: { 
                    value: currentFilters.startTime?.value || null, 
                    type: 'datetime' 
                },
                endTime: { 
                    value: currentFilters.endTime?.value || null, 
                    type: 'datetime' 
                }
            };
            
            // Add/update filters for all discovered columns
            discoveredColumns.forEach(col => {
                // Skip timestamp-related columns since we have dedicated date/time filters
                if (col.key.toLowerCase().includes('time') || col.key.toLowerCase().includes('date') || col.key === 'timestamp') {
                    return;
                }
                const uniqueVals = Array.from(values[col.key] || []).sort();
                updatedFilters[col.key] = {
                    value: currentFilters[col.key]?.value || null,
                    type: uniqueVals.length <= 10 ? 'select' : 'text',
                    options: uniqueVals.length <= 10 ? uniqueVals : undefined
                };
            });
            
            return updatedFilters;
        });
    }, [logEntries]);

    const handleFilterChange = (key: string, value: string | null) => {
        const newFilters = { ...filters, [key]: { ...filters[key], value } };
        setFilters(newFilters);
        onFiltersChange(newFilters);
    };

    const handleQuickTimeRange = (range: string) => {
        const now = new Date();
        let startTime: Date;

        switch (range) {
            case '1h':
                startTime = new Date(now.getTime() - 60 * 60 * 1000);
                break;
            case '3h':
                startTime = new Date(now.getTime() - 3 * 60 * 60 * 1000);
                break;
            case '12h':
                startTime = new Date(now.getTime() - 12 * 60 * 60 * 1000);
                break;
            case '1d':
                startTime = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                break;
            case '3d':
                startTime = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
                break;
            case '1w':
                startTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                break;
            default:
                return;
        }

        // Format as local datetime-local string to match log entry timestamps
        const formatLocalDateTime = (date: Date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0');
            const minutes = String(date.getMinutes()).padStart(2, '0');
            return `${year}-${month}-${day}T${hours}:${minutes}`;
        };

        const startTimeStr = formatLocalDateTime(startTime);
        const endTime = new Date(now.getTime() + 60 * 1000); // Add 1 minute buffer
        const endTimeStr = formatLocalDateTime(endTime);

        const newFilters = {
            ...filters,
            startTime: { ...filters.startTime, value: startTimeStr },
            endTime: { ...filters.endTime, value: endTimeStr }
        };
        setFilters(newFilters);
        onFiltersChange(newFilters);
    };

    const handleExport = async () => {
        try {
            const params = new URLSearchParams();
            
            // Add time filters if set
            if (filters.startTime?.value) {
                params.append('from', filters.startTime.value);
            }
            if (filters.endTime?.value) {
                params.append('to', filters.endTime.value);
            }
            
            // Add other filters
            Object.entries(filters).forEach(([key, filter]) => {
                if (filter.value && key !== 'startTime' && key !== 'endTime') {
                    if (key === 'level') {
                        params.append('level', filter.value);
                    } else if (key === 'name') {
                        params.append('name', filter.value);
                    }
                }
            });
            
            params.append('format', 'csv');
            params.append('limit', '10000');
            
            const url = `/api/logs/download?${params.toString()}`;
            const link = document.createElement('a');
            link.href = url;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Export failed:', error);
            alert('Export failed. Please try again.');
        }
    };

    const renderFilterInput = (column: Column) => {
        const filter = filters[column.key];
        if (!filter) return null;

        switch (filter.type) {
            case 'select':
                return (
                    <select
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                        value={filter.value || ''}
                        onChange={(e) => handleFilterChange(column.key, e.target.value || null)}
                    >
                        <option value="">All</option>
                        {filter.options?.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
                );
            default:
                return (
                    <input
                        type="text"
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                        placeholder={`Filter ${column.label}...`}
                        value={filter.value || ''}
                        onChange={(e) => handleFilterChange(column.key, e.target.value || null)}
                    />
                );
        }
    };

    const renderDateTimeFilter = (key: 'startTime' | 'endTime', label: string) => {
        const filter = filters[key];
        if (!filter) return null;

        return (
            <div className="flex flex-col">
                <label className="block text-sm font-medium text-gray-700">
                    {label}
                </label>
                <input
                    type="datetime-local"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                    value={filter.value || ''}
                    onChange={(e) => handleFilterChange(key, e.target.value || null)}
                />
            </div>
        );
    };

    return (
        <div className="bg-white p-4 rounded-lg shadow mb-4">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Filters</h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleExport}
                        className="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 text-white rounded-md border border-green-700 transition-colors flex items-center gap-1"
                        title="Export filtered logs to CSV"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Export
                    </button>
                    <button
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className="text-gray-500 hover:text-gray-700 focus:outline-none"
                        aria-label={isCollapsed ? 'Expand filters' : 'Collapse filters'}
                    >
                        <svg
                            className={`w-5 h-5 transform transition-transform ${isCollapsed ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                </div>
            </div>
            {!isCollapsed && (
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-3 bg-gray-50 rounded-lg">
                        <h4 className="col-span-full text-sm font-medium text-gray-700 mb-2">Date & Time Range</h4>
                        <div className="col-span-full mb-3">
                            <div className="flex flex-wrap gap-2">
                                {['1h', '3h', '12h', '1d', '3d', '1w'].map(range => (
                                    <button
                                        key={range}
                                        onClick={() => handleQuickTimeRange(range)}
                                        className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-800 rounded-md border border-blue-300 transition-colors"
                                    >
                                        Last {range}
                                    </button>
                                ))}
                                <button
                                    onClick={() => {
                                        const newFilters = {
                                            ...filters,
                                            startTime: { ...filters.startTime, value: null },
                                            endTime: { ...filters.endTime, value: null }
                                        };
                                        setFilters(newFilters);
                                        onFiltersChange(newFilters);
                                    }}
                                    className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md border border-gray-300 transition-colors"
                                    title="Clear time filters"
                                >
                                    Clear
                                </button>
                            </div>
                        </div>
                        {renderDateTimeFilter('startTime', 'Start Time')}
                        {renderDateTimeFilter('endTime', 'End Time')}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {columns.filter(col => 
                            !col.key.toLowerCase().includes('time') && 
                            !col.key.toLowerCase().includes('date') && 
                            col.key !== 'timestamp' &&
                            col.key !== 'thread' &&
                            col.key !== 'process' &&
                            col.key !== 'stack_info' &&
                            col.key !== 'msecs' &&
                            col.key !== 'threadName' &&
                            col.key !== 'processName' &&
                            col.key !== 'relativeCreated'
                        ).filter(col => {
                            const filter = filters[col.key];
                            if (filter?.type === 'select' && filter.options) {
                                return !(filter.options.length === 1 && filter.options[0] === 'None');
                            }
                            return true;
                        }).map(column => (
                            <div key={column.key} className="flex flex-col">
                                <label className="block text-sm font-medium text-gray-700">
                                    {column.label}
                                </label>
                                {renderFilterInput(column)}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
} 