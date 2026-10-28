import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { AccuracyPage } from "./pages/AccuracyPage";
import { ExplorerPage } from "./pages/ExplorerPage";
import { MethodologyPage } from "./pages/MethodologyPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OverviewPage } from "./pages/OverviewPage";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/explorer" element={<ExplorerPage />} />
        <Route path="/accuracy" element={<AccuracyPage />} />
        <Route path="/methodology" element={<MethodologyPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
