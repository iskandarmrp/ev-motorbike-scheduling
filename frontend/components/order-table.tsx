"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, Download } from "lucide-react";
import type { OrderSchedule, MotorbikeState } from "./dashboard-battery-swap";

interface OrderTableProps {
  orderSchedules?: OrderSchedule[];
  motorbikeStates?: Record<string, MotorbikeState>;
}

export function OrderTable({
  orderSchedules = [],
  motorbikeStates = {},
}: OrderTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredOrders = orderSchedules.filter(
    (order) =>
      order.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (order.assigned_motorbike_id &&
        order.assigned_motorbike_id
          .toLowerCase()
          .includes(searchTerm.toLowerCase()))
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
      case "searching driver":
        return "bg-yellow-500";
      case "on going":
        return "bg-blue-500";
      case "done":
        return "bg-green-500";
      case "failed":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search orders..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-sm"
          />
        </div>
        {/* <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button> */}
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Order ID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Origin</TableHead>
              <TableHead>Destination</TableHead>
              <TableHead>Assigned Motorbike ID</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead>Completed At</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredOrders.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center py-8 text-gray-500"
                >
                  No orders found
                </TableCell>
              </TableRow>
            ) : (
              filteredOrders.map((order) => (
                <TableRow key={order.id}>
                  <TableCell className="font-medium">{order.id}</TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(order.status)}>
                      {order.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {order.order_origin_lat.toFixed(4)},{" "}
                    {order.order_origin_lon.toFixed(4)}
                  </TableCell>
                  <TableCell>
                    {order.order_destination_lat.toFixed(4)},{" "}
                    {order.order_destination_lon.toFixed(4)}
                  </TableCell>
                  <TableCell>
                    {order.assigned_motorbike_id ? (
                      <span className="font-medium">
                        Motorbike {order.assigned_motorbike_id}
                      </span>
                    ) : (
                      <span className="text-gray-500">Unassigned</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {new Date(order.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    {order.completed_at ? (
                      new Date(order.completed_at).toLocaleString()
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
