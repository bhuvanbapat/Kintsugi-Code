import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Repositories from "./pages/Repositories";
import Workspace from "./pages/Workspace";
import Explorer from "./pages/Explorer";
import SearchPage from "./pages/Search";
import Symbols from "./pages/Symbols";
import Graph from "./pages/Graph";
import Tests from "./pages/Tests";
import AgentTrace from "./pages/AgentTrace";
import Evaluation from "./pages/Evaluation";
import SettingsPage from "./pages/Settings";
import DiffViewer from "./pages/DiffViewer";
import "./styles.css";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/repos", element: <Repositories /> },
      { path: "/workspace", element: <Workspace /> },
      { path: "/explore", element: <Explorer /> },
      { path: "/search", element: <SearchPage /> },
      { path: "/symbols", element: <Symbols /> },
      { path: "/graph", element: <Graph /> },
      { path: "/tests", element: <Tests /> },
      { path: "/trace", element: <AgentTrace /> },
      { path: "/eval", element: <Evaluation /> },
      { path: "/diff", element: <DiffViewer /> },
      { path: "/settings", element: <SettingsPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
