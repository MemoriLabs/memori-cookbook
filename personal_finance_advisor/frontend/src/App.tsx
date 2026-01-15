import React, { useState } from "react";
import LandingPage from "./components/LandingPage";
import Dashboard from "./components/Dashboard";
import "./styles.css";

type View = "landing" | "dashboard";

function App() {
  const [currentView, setCurrentView] = useState<View>("landing");

  return (
    <>
      {currentView === "landing" && (
        <LandingPage onGetStarted={() => setCurrentView("dashboard")} />
      )}
      {currentView === "dashboard" && (
        <Dashboard onBackToLanding={() => setCurrentView("landing")} />
      )}
    </>
  );
}

export default App;
