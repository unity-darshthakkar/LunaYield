/** LunaYield Layout - Shared site shell wrapper */

import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';
import { PresentationBackdrop } from '../components/presentation';

export function PublicLayout() {
  const location = useLocation();
  const isMissionControl = location.pathname === '/mission-control';

  return (
    <div className="presentation-shell flex flex-col">
      <PresentationBackdrop variant="public" />
      <Header isMissionControl={isMissionControl} />
      <main className="presentation-main" id="main-content" role="main">
        <Outlet />
      </main>
      <Footer variant={isMissionControl ? 'mission-control' : 'public'} />
    </div>
  );
}

export function MissionControlLayout() {
  return (
    <div className="presentation-shell flex flex-col font-mono">
      <PresentationBackdrop variant="mission-control" />
      <Header isMissionControl={true} />
      <main className="mission-main" id="main-content" role="main">
        <Outlet />
      </main>
      <Footer variant="mission-control" />
    </div>
  );
}
