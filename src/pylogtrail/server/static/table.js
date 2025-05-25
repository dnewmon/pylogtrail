class Debouncer {
    constructor(callback, delay) {
        this.callback = callback;
        this.delay = delay;
        this.timeout = null;
    }

    debounce() {
        clearTimeout(this.timeout);
        this.timeout = setTimeout(this.callback, this.delay);
    }
}

export class TableController {
    constructor(table_id) {
        this.table_id = table_id;
        this.table = document.getElementById(table_id);
        this.table_body = this.table.querySelector("tbody");
        this.table_header = this.table.querySelector("thead");
        this.table_footer = this.table.querySelector("tfoot");

        // Add filter state
        this.filters = {
            level: 0,
            name: "",
            startTime: null,
            endTime: null
        };

        this.messageColumn = {
            key: "message",
            label: "Message",
            visible: true,
            render: (value) => {
                const span = document.createElement("span");
                span.classList.add("font-mono");
                span.classList.add("whitespace-pre-wrap");
                if (value.includes("\n")) {
                    span.innerHTML = value.replace(/\n/g, "<br>");
                }
                else {
                    span.innerHTML = value;
                }
                return span;
            }
        }

        this.columns = [{
            key: "timestamp",
            label: "Timestamp",
            visible: true,
            render: (value) => new Date(value).toLocaleString()
        }, {
            key: "level",
            label: "Level",
            visible: true,
            render: (value) => {
                const span = document.createElement("span");
                if (value === "DEBUG") {
                    span.classList.add("text-gray-500");
                } else if (value === "INFO") {
                    span.classList.add("text-green-500");
                } else if (value === "WARNING") {
                    span.classList.add("text-yellow-300");
                } else if (value === "ERROR") {
                    span.classList.add("text-red-500");
                }
                span.innerHTML = value;
                return span;
            }
        }, {
            key: "name",
            label: "Name",
            visible: true,
        }];

        this.log_entries = [];

        this.update_debouncer = new Debouncer(() => {
            this.renderTable();
        }, 100);
    }

    isColumn(key) {
        return this.columns.some(column => column.key === key);
    }

    keyToLabel(key) {
        return key.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase());
    }

    discoverColumns() {
        this.log_entries.forEach(log_entry => {
            Object.keys(log_entry).forEach(key => {
                if (!this.isColumn(key)) {
                    this.columns.push({
                        key: key,
                        label: this.keyToLabel(key),
                        visible: false
                    });
                }
            });
        });
    }

    addLogEntry(log_entry) {
        this.log_entries.unshift(log_entry);
        this.log_entries.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        this.discoverColumns();
        this.update_debouncer.debounce();
    }

    renderCell(column, cell_value) {
        const td = document.createElement("td");
        if (!column.visible) {
            td.classList.add("hidden");
        }

        td.classList.add("text-nowrap");
        td.classList.add("px-3");

        if (column.key === "message") {
            td.classList.add("w-full");
        } else {
            td.classList.add("w-min");
        }

        if (column.render) {
            const cell_content = column.render(cell_value);
            if (cell_content instanceof Node) {
                td.appendChild(cell_content);
            } else {
                td.innerHTML = cell_content;
            }
        } else {
            td.innerHTML = `${cell_value}`;
        }
        return td;
    }

    renderRow(log_entry) {
        const row = document.createElement("tr");
        this.columns.forEach(column => {
            const cell = this.renderCell(column, log_entry[column.key]);
            row.appendChild(cell);
        });

        const message_cell = this.renderCell(this.messageColumn, log_entry.message);
        row.appendChild(message_cell);

        return row;
    }

    renderColumnHeader(column) {
        const th = document.createElement("th");
        th.innerHTML = column.label;
        if (!column.visible) {
            th.classList.add("hidden");
        }
        return th;
    }

    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        this.update_debouncer.debounce();
    }

    filterLogEntry(log_entry) {
        // Filter by level
        if (this.filters.level && log_entry.level !== this.filters.level) {
            return false;
        }

        // Filter by logger name
        if (this.filters.name && !log_entry.name.toLowerCase().includes(this.filters.name.toLowerCase())) {
            return false;
        }

        // Filter by time range
        const logTime = new Date(log_entry.timestamp);
        if (this.filters.startTime && logTime < this.filters.startTime) {
            return false;
        }
        if (this.filters.endTime && logTime > this.filters.endTime) {
            return false;
        }

        return true;
    }

    renderTable() {
        const start = performance.now();

        this.table_header.innerHTML = "";

        this.columns.forEach(column => {
            const th = this.renderColumnHeader(column);
            this.table_header.appendChild(th);
        });

        const th = this.renderColumnHeader(this.messageColumn);
        this.table_header.appendChild(th);

        this.table_body.innerHTML = "";

        // Filter and render log entries
        const filtered_entries = this.log_entries.filter(entry => this.filterLogEntry(entry));

        filtered_entries.forEach((log_entry, index) => {
            const is_odd = index % 2 === 1;
            const row = this.renderRow(log_entry);
            row.classList.add("hover:bg-gray-100");
            row.classList.add("border-t-1");
            row.classList.add("border-t-gray-200");

            /*if (log_entry.level === "ERROR") {
                row.classList.add(is_odd ? "bg-red-100" : "bg-red-200");
                row.classList.add("hover:bg-red-300");
            }
            else if (log_entry.level === "WARNING") {
                row.classList.add(is_odd ? "bg-yellow-100" : "bg-yellow-200");
                row.classList.add("hover:bg-yellow-300");
            }
            else if (log_entry.level === "INFO") {
                row.classList.add(is_odd ? "bg-green-100" : "bg-green-200");
                row.classList.add("hover:bg-green-300");
            }
            else if (log_entry.level === "DEBUG") {
                row.classList.add(is_odd ? "bg-blue-100" : "bg-blue-200");
                row.classList.add("hover:bg-blue-300");
            }*/

            this.table_body.appendChild(row);
        });

        const end = performance.now();
    }
}
