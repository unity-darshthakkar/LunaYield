/** LunaYield Mission Lab - Main Application with React Router */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { ProblemSolutionPage } from './pages/ProblemSolutionPage';
import { MissionControlPage } from './pages/MissionControlPage';
import { TechArchitectureDemoPage } from './pages/TechArchitectureDemoPage';
import { PublicLayout, MissionControlLayout } from './layout/Layout';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<PublicLayout />}>
          <Route index element={<HomePage />} />
          <Route path="problem-solution" element={<ProblemSolutionPage />} />
          <Route path="tech" element={<TechArchitectureDemoPage />} />
        </Route>

        <Route path="/mission-control" element={<MissionControlLayout />}>
          <Route index element={<MissionControlPage />} />
        </Route>

        <Route path="*" element={<HomePage />} />
      </Routes>
    </Router>
  );
}