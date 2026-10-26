"use client";

import { useState } from "react";

export default function LoginPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");

  return (
    <main className="min-h-screen flex items-center justify-center bg-dark-surface">
      <div className="w-full max-w-sm">
        <div className="flex bg-white/5 rounded-full p-1 mb-9">
          <button
            onClick={() => setMode("signin")}
            className={`flex-1 py-2.5 rounded-full text-sm font-medium ${
              mode === "signin" ? "bg-sage text-charcoal" : "text-muted"
            }`}
          >
            Sign in
          </button>
          <button
            onClick={() => setMode("signup")}
            className={`flex-1 py-2.5 rounded-full text-sm font-medium ${
              mode === "signup" ? "bg-sage text-charcoal" : "text-muted"
            }`}
          >
            Sign up
          </button>
        </div>

        <h1 className="text-2xl font-bold text-text mb-1">
          {mode === "signin" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="text-muted text-sm mb-8">
          {mode === "signin" ? "Log in to see your saved analyses." : "Start finding the cracks in your plans."}
        </p>

        <div className="space-y-5">
          <div>
            <label className="block text-muted text-sm mb-2">Email</label>
            <input
              type="email"
              placeholder="you@example.com"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-text outline-none focus:border-sage"
            />
          </div>
          <div>
            <label className="block text-muted text-sm mb-2">Password</label>
            <input
              type="password"
              placeholder="••••••••"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-text outline-none focus:border-sage"
            />
          </div>
        </div>

        <button className="w-full mt-8 bg-sage text-charcoal font-semibold py-3 rounded-full">
          {mode === "signin" ? "Sign in" : "Sign up"}
        </button>
      </div>
    </main>
  );
}