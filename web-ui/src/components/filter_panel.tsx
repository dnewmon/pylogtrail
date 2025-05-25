import { useState, useEffect } from 'react';
import type { Column } from './table';
import type { LogEntry } from './log_entry';
import { discoverColumns } from './table';

export interface DynamicFilters {
    [key: string]: {
        value: string | null;
        type: 'text' | 'select' | 'date';
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
    const [_uniqueValues, setUniqueValues] = useState<{ [key: string]: Set<string> }>({});

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

        // Initialize filters
        const initialFilters: DynamicFilters = {};
        discoveredColumns.forEach(col => {
            const uniqueVals = Array.from(values[col.key] || []);
            initialFilters[col.key] = {
                value: null,
                type: uniqueVals.length <= 10 ? 'select' : 
                      col.key.toLowerCase().includes('time') || col.key.toLowerCase().includes('date') ? 'date' : 'text',
                options: uniqueVals.length <= 10 ? uniqueVals : undefined
            };
        });
        setFilters(initialFilters);
    }, [logEntries]);

    const handleFilterChange = (key: string, value: string | null) => {
        const newFilters = { ...filters, [key]: { ...filters[key], value } };
        setFilters(newFilters);
        onFiltersChange(newFilters);
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
            case 'date':
                return (
                    <input
                        type="datetime-local"
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                        value={filter.value || ''}
                        onChange={(e) => handleFilterChange(column.key, e.target.value || null)}
                    />
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

    return (
        <div className="bg-white p-4 rounded-lg shadow mb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Filters</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {columns.map(column => (
                    <div key={column.key} className="flex flex-col">
                        <label className="block text-sm font-medium text-gray-700">
                            {column.label}
                        </label>
                        {renderFilterInput(column)}
                    </div>
                ))}
            </div>
        </div>
    );
} 