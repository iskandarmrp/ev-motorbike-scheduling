// Mock data for preview environments

// Sample taxi data
export const mockTaxiStates = {
  "0": {
    taxi_state: "kosong",
    latitude: -6.8993,
    longitude: 107.6405,
    battery: 85,
  },
  "1": {
    taxi_state: "menuju penumpang",
    latitude: -6.918,
    longitude: 107.6095,
    battery: 72,
  },
  "2": {
    taxi_state: "bersama penumpang",
    latitude: -6.9211,
    longitude: 107.6095,
    battery: 63,
  },
}

// Sample base data
export const mockBaseStates = {
  "1001": {
    latitude: -6.8993,
    longitude: 107.6405,
    fleet: [0, null, null],
  },
  "1002": {
    latitude: -6.918,
    longitude: 107.6095,
    fleet: [null, null, null],
  },
  "1003": {
    latitude: -6.9211,
    longitude: 107.6095,
    fleet: [null, null, null, null, null],
  },
}

// Sample assignments
export const mockAssignments = {
  "1": {
    base_id: "1001",
    polyline: "yvri@ya}eTnCkBdEwC",
    deviate_radius: 2000,
  },
}

// Sample base requests
export const mockBaseRequests = ["1002", "1003", "1003"]

// Sample base activity logs
export const mockBaseActivityLogs = [
  {
    timestamp: "2023-05-15T08:30:00.000Z",
    base_id: "1001",
    status: "taxi masuk",
    taxi_id: "0",
  },
  {
    timestamp: "2023-05-15T09:45:00.000Z",
    base_id: "1001",
    status: "taxi keluar",
    taxi_id: "0",
  },
  {
    timestamp: "2023-05-15T10:15:00.000Z",
    base_id: "1002",
    status: "taxi masuk",
    taxi_id: "2",
  },
  {
    timestamp: "2023-05-15T11:30:00.000Z",
    base_id: "1002",
    status: "taxi keluar",
    taxi_id: "2",
  },
  {
    timestamp: "2023-05-16T08:00:00.000Z",
    base_id: "1003",
    status: "taxi masuk",
    taxi_id: "1",
  },
]

// Sample violation logs
export const mockViolationLogs = [
  {
    timestamp: "2023-05-15T09:15:00.000Z",
    taxi_id: "1",
    base_id: "1001",
    reason: "Timeout (melewati batas waktu)",
  },
  {
    timestamp: "2023-05-15T14:30:00.000Z",
    taxi_id: "2",
    base_id: "1002",
    reason: "melenceng pada titik latitude -6.9100 dan longitude 107.6200",
  },
  {
    timestamp: "2023-05-16T10:45:00.000Z",
    taxi_id: "0",
    base_id: "1003",
    reason: "Timeout (melewati batas waktu)",
  },
]

// Mock login function
export function mockLogin(options: RequestInit) {
  try {
    const body = JSON.parse(options.body as string)

    // Simple validation
    if (body.username && body.password) {
      return {
        token: "mock-token-12345",
        user_id: "mock-user-id",
        message: "Login successful",
      }
    } else {
      throw new Error("Invalid credentials")
    }
  } catch (error) {
    throw new Error("Invalid request format")
  }
}

// Mock register function
export function mockRegister(options: RequestInit) {
  try {
    const body = JSON.parse(options.body as string)

    // Simple validation
    if (body.username && body.name && body.password) {
      return {
        token: "mock-token-12345",
        user_id: "mock-user-id",
      }
    } else {
      throw new Error("Missing required fields")
    }
  } catch (error) {
    throw new Error("Invalid request format")
  }
}
