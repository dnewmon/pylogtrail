import React, { useCallback, useMemo } from 'react';
import type { LogEntry } from './log_entry';
import type { DynamicFilters } from './filter_panel';

export interface Column {
    key: string;
    label: string;
    visible: boolean;
    render?: (value: any) => React.ReactNode;
}

export interface TableProps {
    logEntries: LogEntry[];
    columns: Column[];
    filters?: DynamicFilters;
}

export const discoverColumns = (entries: LogEntry[], existingColumns: Column[] = []): Column[] => {
    const newColumns = [...existingColumns];
    entries.forEach(entry => {
        Object.keys(entry).forEach(key => {
            if (!newColumns.some(col => col.key === key)) {
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
        render: (value: string) => new Date(value).toLocaleString()
    },
    {
        key: "level",
        label: "Level",
        visible: true,
        render: (value: string) => {
            const colorClass = {
                'DEBUG': 'text-gray-500',
                'INFO': 'text-green-500',
                'WARNING': 'text-yellow-300',
                'ERROR': 'text-red-500'
            }[value] || '';
            return <span className={colorClass}>{value}</span>;
        }
    },
    {
        key: "name",
        label: "Name",
        visible: true,
    }
];

export const messageColumn: Column = {
    key: "message",
    label: "Message",
    visible: true,
    render: (value: string) => (
        <span className="font-mono whitespace-pre-wrap">
            {value.split('\n').map((line, i) => (
                <React.Fragment key={i}>
                    {i > 0 && <br />}
                    {line}
                </React.Fragment>
            ))}
        </span>
    )
};

export default function LogTable({ logEntries, columns, filters }: TableProps) {
    const filterLogEntry = useCallback((entry: LogEntry) => {
        if (!filters) return true;
        
        return Object.entries(filters).every(([key, filter]) => {
            if (!filter.value) return true;
            
            const entryValue = entry[key];
            if (entryValue === undefined || entryValue === null) return false;
            
            const entryStr = String(entryValue).toLowerCase();
            const filterStr = filter.value.toLowerCase();
            
            // Handle date fields
            if (filter.type === 'date') {
                const entryDate = new Date(entryValue);
                const filterDate = new Date(filter.value);
                return !isNaN(entryDate.getTime()) && !isNaN(filterDate.getTime()) && 
                       entryDate.getTime() === filterDate.getTime();
            }
            
            // For select and text fields, do a simple includes check
            return entryStr.includes(filterStr);
        });
    }, [filters]);

    const filteredEntries = useMemo(() => 
        logEntries.filter(filterLogEntry),
        [logEntries, filterLogEntry]
    );

    const renderCell = (column: Column, value: any) => {
        const cellContent = column.render ? column.render(value) : value;
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
                    {filteredEntries.map((entry, index) => (
                        <tr 
                            key={`${entry.timestamp}-${index}`}
                            className="hover:bg-gray-100 border-t border-t-gray-200"
                        >
                            {columns.map(column => renderCell(column, entry[column.key]))}
                            {renderCell(messageColumn, entry.message)}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
