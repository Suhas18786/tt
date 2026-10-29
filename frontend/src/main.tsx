import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./auth";
import { LookupsProvider } from "./lookups";
import { ToastProvider } from "./ui";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <LookupsProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </LookupsProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
