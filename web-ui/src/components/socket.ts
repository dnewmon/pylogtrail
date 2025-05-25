import {io, Socket} from 'socket.io-client';
import type { LogEntry } from './log_entry';

interface WriteSocketEvents {
    get_initial_logs: (limit: number) => void;
}

export interface InitialLogsResponse {
    logs: LogEntry[];
}

interface ReadSocketEvents {
    connect: () => void;
    disconnect: () => void;
    new_log: (log: LogEntry) => void;
    initial_logs: (logs: InitialLogsResponse) => void;
}

export class SocketHandler {
    private socket: Socket<ReadSocketEvents, WriteSocketEvents>;
    public is_connected: boolean;

    constructor() {
        this.socket = io();
        this.is_connected = false;

        this.on_connect(() => {
            console.log("Connected to websocket");
            this.is_connected = true;
        });

        this.on_disconnect(() => {
            console.log("Disconnected from websocket");
            this.is_connected = false;
        });
    }

    get_initial_logs(limit: number) {
        this.socket.emit("get_initial_logs", limit);
    }

    on_connect(callback: () => void) {
        this.socket.on("connect", callback);
    }

    on_disconnect(callback: () => void) {
        this.socket.on("disconnect", callback);
    }

    on_new_log(callback: (log: LogEntry) => void) {
        this.socket.on("new_log", callback);
    }

    on_initial_logs(callback: (initial_logs: InitialLogsResponse) => void) {
        this.socket.on("initial_logs", callback);
    }
}
