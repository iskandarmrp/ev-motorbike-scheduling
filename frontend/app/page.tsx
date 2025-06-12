"use client";

import { useEffect, useState } from "react";
import { LoginPage } from "@/components/login-page";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function Home() {
  // Check if user is logged in (this is a simple check, in real app you'd check token validity)
  const [isLoggedIn, setIsLoggedIn] = useState<boolean | null>(null);
  // const isLoggedIn =
  //   typeof window !== "undefined" && localStorage.getItem("token");

  useEffect(() => {
    const token = localStorage.getItem("token");
    setIsLoggedIn(!!token);
  }, []);

  if (isLoggedIn) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-md">
          <h1 className="text-2xl font-bold mb-6 text-center">
            Fleet Management System
          </h1>
          <div className="space-y-4">
            <Link href="/dashboard">
              <Button className="w-full bg-green-600 hover:bg-green-700">
                Taxi Listrik (Taxi System)
              </Button>
            </Link>
            <Link href="/battery-swap">
              <Button className="w-full bg-purple-600 hover:bg-purple-700">
                Electric Fleet Management (Battery Swap)
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <LoginPage />;
}
