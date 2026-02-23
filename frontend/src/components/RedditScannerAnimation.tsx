"use client"

import { useEffect, useState } from "react"

interface RedditScannerAnimationProps {
  isComplete?: boolean
}

export default function RedditScannerAnimation({ isComplete = false }: RedditScannerAnimationProps) {
  const [scanAngle, setScanAngle] = useState(0)

  useEffect(() => {
    if (isComplete) return

    const interval = setInterval(() => {
      setScanAngle((prev) => (prev + 3) % 360)
    }, 30)

    return () => clearInterval(interval)
  }, [isComplete])

  return (
    <div className="relative w-32 h-32 flex items-center justify-center">
      {/* Reddit Snoo Icon */}
      <svg viewBox="0 0 100 100" className="w-24 h-24" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Orange circle background */}
        <circle cx="50" cy="50" r="45" fill="#FF4500" />

        {/* Snoo face (white) */}
        <ellipse cx="50" cy="55" rx="28" ry="24" fill="white" />

        {/* Antenna */}
        <circle cx="68" cy="18" r="6" fill="white" />
        <path d="M50 30 Q55 20 62 18" stroke="#1A1A1B" strokeWidth="3" fill="none" strokeLinecap="round" />

        {/* Left ear */}
        <ellipse cx="26" cy="40" rx="8" ry="8" fill="white" />

        {/* Right ear */}
        <ellipse cx="74" cy="40" rx="8" ry="8" fill="white" />

        {/* Left eye */}
        <ellipse cx="38" cy="52" rx="6" ry="7" fill="#FF4500" />
        <circle cx="40" cy="50" r="2" fill="white" />

        {/* Right eye */}
        <ellipse cx="62" cy="52" rx="6" ry="7" fill="#FF4500" />
        <circle cx="64" cy="50" r="2" fill="white" />

        {/* Smile */}
        <path d="M40 68 Q50 76 60 68" stroke="#1A1A1B" strokeWidth="3" fill="none" strokeLinecap="round" />
      </svg>

      {/* Scanning magnifying glass */}
      <div
        className="absolute"
        style={{
          transform: `rotate(${scanAngle}deg)`,
          transformOrigin: "center center",
        }}
      >
        <div
          className="absolute"
          style={{
            left: "50%",
            top: "-8px",
            transform: "translateX(-50%)",
          }}
        >
          <svg viewBox="0 0 40 40" className="w-10 h-10" fill="none" xmlns="http://www.w3.org/2000/svg">
            {/* Magnifying glass circle */}
            <circle
              cx="16"
              cy="16"
              r="10"
              stroke="hsl(var(--foreground))"
              strokeWidth="3"
              fill="none"
              className="opacity-80"
            />
            {/* Glass fill with gradient effect */}
            <circle cx="16" cy="16" r="8" fill="hsl(var(--secondary))" className="opacity-20" />
            {/* Handle */}
            <line
              x1="24"
              y1="24"
              x2="34"
              y2="34"
              stroke="hsl(var(--foreground))"
              strokeWidth="3"
              strokeLinecap="round"
              className="opacity-80"
            />
          </svg>
        </div>
      </div>

      {/* Scanning beam effect */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `conic-gradient(from ${scanAngle}deg at 50% 50%, transparent 0deg, hsl(var(--secondary) / 0.3) 15deg, transparent 30deg)`,
        }}
      />

      {/* Pulse rings */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div
          className="absolute w-28 h-28 rounded-full border-2 border-secondary/30 animate-ping"
          style={{ animationDuration: "2s" }}
        />
        <div
          className="absolute w-36 h-36 rounded-full border border-secondary/20 animate-ping"
          style={{ animationDuration: "3s", animationDelay: "0.5s" }}
        />
      </div>

      {/* Complete checkmark overlay */}
      {isComplete && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 rounded-full">
          <svg
            viewBox="0 0 24 24"
            className="w-12 h-12 text-green-500"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
      )}
    </div>
  )
}
