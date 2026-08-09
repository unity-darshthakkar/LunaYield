/** Route panel displaying the active route waypoints as an ordered timeline */

import type { MissionRoute, RouteWaypoint } from '../types/mission';
import { clsx } from 'clsx';

interface RoutePanelProps {
  activeRoute: MissionRoute | undefined;
  originalRoute: MissionRoute | undefined;
  className?: string;
}

function WaypointItem({
  waypoint,
  index,
}: {
  waypoint: RouteWaypoint;
  index: number;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <div className="w-3 h-3 rounded-full bg-gray-600 border-2 border-gray-900 z-10" />
        {index > 0 && (
          <div className="w-0.5 h-full bg-gray-700 mt-1" />
        )}
        {index > 0 && (
          <div className="w-0.5 h-full bg-gray-700" />
        )}
      </div>
      <div className="flex-1 min-w-0 pt-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-medium text-white">
            {waypoint.label}
          </span>
          {waypoint.is_science_target && (
            <span className="px-1.5 py-0.5 text-[10px] font-mono bg-blue-900/50 text-blue-300 rounded border border-blue-800">
              SCIENCE
            </span>
          )}
        </div>
        <div className="text-[10px] text-gray-500 font-mono mt-0.5">
          ID: {waypoint.id} | Pos: ({waypoint.x.toFixed(2)}, {waypoint.y.toFixed(2)})
        </div>
      </div>
    </div>
  );
}

export function RoutePanel({
  activeRoute,
  originalRoute,
  className = '',
}: RoutePanelProps) {
  const route = activeRoute ?? originalRoute;

  if (!route) {
    return (
      <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
        <h3 className="text-sm font-semibold text-gray-300 mb-3">ACTIVE ROUTE</h3>
        <p className="text-gray-500 text-sm">No route data available</p>
      </div>
    );
  }

  return (
    <div className={clsx('p-4 bg-gray-900/50 rounded-lg border border-gray-700', className)}>
      <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-blue-500" />
        ACTIVE ROUTE
        <span className="text-xs text-gray-500 font-mono">
          ({route.waypoints.length} waypoints)
        </span>
      </h3>
      <div className="space-y-4">
        {route.waypoints.map((waypoint, index) => (
          <WaypointItem
            key={waypoint.id}
            waypoint={waypoint}
            index={index}
          />
        ))}
      </div>
    </div>
  );
}