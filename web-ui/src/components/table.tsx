import React, { useCallback, useMemo, useState } from 'react';
import type { LogEntry } from './log_entry';
import type { DynamicFilters } from './filter_panel';

export interface Column {
    key: string;
    label: string;
    visible: boolean;
    render?: (value: unknown) => React.ReactNode;
}

export interface TableProps {
    logEntries: LogEntry[];
    columns: Column[];
    filters?: DynamicFilters;
}

export const discoverColumns = (entries: LogEntry[], existingColumns: Column[] = []): Column[] => {
    const hiddenFields = ['levelno', 'asctime', 'udp_client_host', 'udp_client_port', 'taskName', 'lineno'];
    const newColumns = [...existingColumns];
    entries.forEach(entry => {
        Object.keys(entry).forEach(key => {
            if (!hiddenFields.includes(key) && !newColumns.some(col => col.key === key)) {
                newColumns.push({
                    key,
                    label: key.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase()),
                    visible: false
                });
            }
        });
    });
    return newColumns;
};

export const defaultColumns: Column[] = [
    {
        key: "timestamp",
        label: "Timestamp",
        visible: true,
        render: (value: unknown) => new Date(String(value)).toLocaleString()
    },
    {
        key: "level",
        label: "Level",
        visible: true,
        render: (value: unknown) => {
            const strValue = String(value);
            const colorClass = {
                'DEBUG': 'text-gray-500',
                'INFO': 'text-green-500',
                'WARNING': 'text-yellow-300',
                'ERROR': 'text-red-500'
            }[strValue] || '';
            return <span className={colorClass}>{strValue}</span>;
        }
    },
    {
        key: "name",
        label: "Name",
        visible: true,
    }
];

export const messageColumn: Column = {
    key: "msg",
    label: "Message",
    visible: true,
    render: (value: unknown) => (
        <span className="font-mono whitespace-pre-wrap">
            {String(value).split('\n').map((line, i) => (
                <React.Fragment key={i}>
                    {i > 0 && <br />}
                    {line}
                </React.Fragment>
            ))}
        </span>
    )
};

export default function LogTable({ logEntries, columns, filters }: TableProps) {
    const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

    const toggleRowExpansion = (entryId: string) => {
        const newExpanded = new Set(expandedRows);
        if (newExpanded.has(entryId)) {
            newExpanded.delete(entryId);
        } else {
            newExpanded.add(entryId);
        }
        setExpandedRows(newExpanded);
    };

    const filterLogEntry = useCallback((entry: LogEntry) => {
        if (!filters) return true;
        
        return Object.entries(filters).every(([key, filter]) => {
            if (!filter.value) return true;
            
            // Handle date/time range filters
            if (key === 'startTime') {
                const entryDate = new Date(entry.timestamp);
                const startDate = new Date(filter.value);
                return !isNaN(entryDate.getTime()) && !isNaN(startDate.getTime()) && 
                       entryDate.getTime() >= startDate.getTime();
            }
            
            if (key === 'endTime') {
                const entryDate = new Date(entry.timestamp);
                const endDate = new Date(filter.value);
                return !isNaN(entryDate.getTime()) && !isNaN(endDate.getTime()) && 
                       entryDate.getTime() <= endDate.getTime();
            }
            
            
            const entryValue = entry[key];
            if (entryValue === undefined || entryValue === null) return false;
            
            const entryStr = String(entryValue).toLowerCase();
            const filterStr = filter.value.toLowerCase();
            
            // For select and text fields, do a simple includes check
            return entryStr.includes(filterStr);
        });
    }, [filters]);

    const filteredEntries = useMemo(() => 
        logEntries.filter(filterLogEntry),
        [logEntries, filterLogEntry]
    );

    const renderCell = (column: Column, value: unknown) => {
        const cellContent = column.render ? column.render(value) : String(value || '');
        return (
            <td 
                key={column.key}
                className={`px-3 text-nowrap ${!column.visible ? 'hidden' : ''} ${
                    column.key === 'message' ? 'w-full' : 'w-min'
                }`}
            >
                {cellContent}
            </td>
        );
    };

    return (
        <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-8">
                            {/* Expand/Collapse column */}
                        </th>
                        {columns.map(column => (
                            <th 
                                key={column.key}
                                className={`px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider ${
                                    !column.visible ? 'hidden' : ''
                                }`}
                            >
                                {column.label}
                            </th>
                        ))}
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            {messageColumn.label}
                        </th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {filteredEntries.map((entry, index) => {
                        const entryId = `${entry.timestamp}-${index}`;
                        const isExpanded = expandedRows.has(entryId);
                        const allFields = Object.entries(entry).filter(([key]) => 
                            !['timestamp', 'level', 'name', 'msg'].includes(key)
                        );
                        
                        return (
                            <React.Fragment key={entryId}>
                                <tr className="hover:bg-gray-100 border-t border-t-gray-200">
                                    <td className="px-3 py-2 w-8">
                                        <button
                                            onClick={() => toggleRowExpansion(entryId)}
                                            className="text-gray-500 hover:text-gray-700 focus:outline-none"
                                            aria-label={isExpanded ? 'Collapse row' : 'Expand row'}
                                        >
                                            <svg
                                                className={`w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                                                fill="none"
                                                stroke="currentColor"
                                                viewBox="0 0 24 24"
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                        </button>
                                    </td>
                                    {columns.map(column => renderCell(column, entry[column.key]))}
                                    {renderCell(messageColumn, entry.msg)}
                                </tr>
                                {isExpanded && allFields.length > 0 && (
                                    <tr className="bg-gray-50">
                                        <td></td>
                                        <td colSpan={columns.filter(c => c.visible).length + 1} className="px-3 py-4">
                                            <div className="text-sm">
                                                <h4 className="font-medium text-gray-900 mb-2">Additional Metadata</h4>
                                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                                    {allFields.map(([key, value]) => (
                                                        <div key={key} className="flex flex-col">
                                                            <span className="font-medium text-gray-700 text-xs">
                                                                {key.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())}
                                                            </span>
                                                            <span className="text-gray-600 font-mono text-xs break-all">
                                                                {String(value)}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </React.Fragment>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
