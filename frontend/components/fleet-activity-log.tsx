"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Download, Filter } from "lucide-react";

interface FleetActivityLogProps {
  logs?: string[];
}

export function FleetActivityLog({ logs = [] }: FleetActivityLogProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [filter, setFilter] = useState("all");

  const filteredLogs = logs.filter((log) => {
    if (searchTerm && !log.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }

    if (filter === "error" && !log.toLowerCase().includes("error")) {
      return false;
    }

    if (filter === "warning" && !log.toLowerCase().includes("warning")) {
      return false;
    }

    if (filter === "info" && !log.toLowerCase().includes("system")) {
      return false;
    }

    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-sm"
          />
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-1">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">All Logs</option>
              <option value="error">Errors</option>
              <option value="warning">Warnings</option>
              <option value="info">System Info</option>
            </select>
          </div>
          {/* <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button> */}
        </div>
      </div>

      <div className="rounded-md border p-4 bg-gray-50 h-96 overflow-y-auto">
        {filteredLogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No logs found</div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log, index) => (
              <div
                key={index}
                className={`p-2 rounded text-sm ${
                  log.includes("error")
                    ? "bg-red-50 text-red-800"
                    : log.includes("warning")
                    ? "bg-yellow-50 text-yellow-800"
                    : "bg-white text-gray-800"
                }`}
              >
                {log}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
