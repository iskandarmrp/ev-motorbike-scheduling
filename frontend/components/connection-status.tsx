"use client"

import { useState, useEffect } from "react"
import { AlertCircle, CheckCircle, WifiOff, RefreshCw } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { API_BASE_URL, BATTERY_API_BASE_URL, DEMO_MODE } from "@/lib/config"
import { fetchBatteryRoot } from "@/lib/battery-api"

export function ConnectionStatus() {
  const [taxiStatus, setTaxiStatus] = useState<"checking" | "connected" | "disconnected">("checking")
  const [batteryStatus, setBatteryStatus] = useState<"checking" | "connected" | "disconnected">("checking")
  const [taxiDetails, setTaxiDetails] = useState("")
  const [batteryDetails, setBatteryDetails] = useState("")
  const [isRetrying, setIsRetrying] = useState(false)

  const checkTaxiConnection = async () => {
    setTaxiStatus("checking")
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      })

      if (response.ok) {
        setTaxiStatus("connected")
        setTaxiDetails(`Taxi system connected to ${API_BASE_URL}`)
      } else {
        setTaxiStatus("disconnected")
        setTaxiDetails(`Taxi server responded with status: ${response.status}`)
      }
    } catch (error) {
      setTaxiStatus("disconnected")
      setTaxiDetails(
        `Failed to connect to taxi system at ${API_BASE_URL}: ${error instanceof Error ? error.message : String(error)}`,
      )
    }
  }

  const checkBatteryConnection = async () => {
    setBatteryStatus("checking")

    if (DEMO_MODE) {
      setBatteryStatus("connected")
      setBatteryDetails("Running in demo mode - using mock data")
      return
    }

    try {
      // Use the battery API function
      await fetchBatteryRoot()
      setBatteryStatus("connected")
      setBatteryDetails(`Battery swap system connected to ${BATTERY_API_BASE_URL} - Using real API data`)
    } catch (error) {
      setBatteryStatus("disconnected")
      const errorMessage = error instanceof Error ? error.message : String(error)
      setBatteryDetails(`Failed to connect to battery system at ${BATTERY_API_BASE_URL}. Error: ${errorMessage}`)
    }
  }

  const checkAllConnections = async () => {
    setIsRetrying(true)
    await Promise.all([checkTaxiConnection(), checkBatteryConnection()])
    setIsRetrying(false)
  }

  useEffect(() => {
    checkAllConnections()
    // Check connections every 30 seconds
    const interval = setInterval(checkAllConnections, 30000)
    return () => clearInterval(interval)
  }, [])

  // Show battery connection status if we're on the battery swap page
  const showBatteryStatus = typeof window !== "undefined" && window.location.pathname.includes("battery-swap")

  if (showBatteryStatus) {
    if (batteryStatus === "connected") {
      return (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-500" />
          <AlertTitle className="text-green-700">Battery System Connected</AlertTitle>
          <AlertDescription className="text-green-600">{batteryDetails}</AlertDescription>
        </Alert>
      )
    }

    if (batteryStatus === "disconnected") {
      return (
        <Alert variant="destructive">
          <WifiOff className="h-4 w-4" />
          <AlertTitle>Battery System Connection Error</AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>{batteryDetails}</span>
            <div className="text-sm text-muted-foreground">
              <p>To fix this issue:</p>
              <ul className="list-disc list-inside ml-2">
                <li>
                  Make sure your FastAPI backend is running: <code>uvicorn app:app --host 0.0.0.0 --port 8000</code>
                </li>
                <li>Check that CORS is configured in your FastAPI app</li>
                <li>Verify no firewall is blocking port 8000</li>
                <li>
                  Try accessing{" "}
                  <a href="http://localhost:8000" target="_blank" rel="noopener noreferrer" className="underline">
                    http://localhost:8000
                  </a>{" "}
                  directly
                </li>
              </ul>
            </div>
            <Button size="sm" onClick={checkBatteryConnection} className="self-start" disabled={isRetrying}>
              {isRetrying ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                "Retry Battery Connection"
              )}
            </Button>
          </AlertDescription>
        </Alert>
      )
    }

    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Checking Battery System Connection</AlertTitle>
        <AlertDescription>Verifying connection to the battery swap backend server...</AlertDescription>
      </Alert>
    )
  }

  // Show taxi connection status for other pages
  if (taxiStatus === "connected") {
    return (
      <Alert className="bg-green-50 border-green-200">
        <CheckCircle className="h-4 w-4 text-green-500" />
        <AlertTitle className="text-green-700">Taxi System Connected</AlertTitle>
        <AlertDescription className="text-green-600">{taxiDetails}</AlertDescription>
      </Alert>
    )
  }

  if (taxiStatus === "disconnected") {
    return (
      <Alert variant="destructive">
        <WifiOff className="h-4 w-4" />
        <AlertTitle>Taxi System Connection Error</AlertTitle>
        <AlertDescription className="flex flex-col gap-2">
          <span>{taxiDetails}</span>
          <Button size="sm" onClick={checkTaxiConnection} className="self-start">
            Retry Taxi Connection
          </Button>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <Alert>
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Checking Taxi System Connection</AlertTitle>
      <AlertDescription>Verifying connection to the taxi backend server...</AlertDescription>
    </Alert>
  )
}
