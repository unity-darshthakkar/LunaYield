/** Route panel displaying the active route waypoints as an ordered timeline */

import type { MissionRoute, RouteWaypoint } from '../types/mission';
import { clsx } from 'clsx';

interface RoutePanelProps {
  activeRoute: MissionRoute | undefined;
  originalRoute: MissionRoute | undefined;
  approvedPlanLabel?: string;
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
        <div className="z-10 h-3 w-3 rounded-full border-2 border-gray-900 bg-gray-600" />
        {index > 0 && <div className="h-full w-0.5 bg-gray-700" />}
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-white">{waypoint.label}</span>
          {waypoint.is_science_target && (
            <span className="rounded border border-blue-800 bg-blue-900/50 px-1.5 py-0.5 text-[10px] font-mono text-blue-300">
              SCIENCE
            </span>
          )}
        </div>
        <div className="mt-1 break-words text-[10px] font-mono leading-relaxed text-gray-500">
          ID: {waypoint.id} | Pos: ({waypoint.x.toFixed(2)}, {waypoint.y.toFixed(2)})
        </div>
      </div>
    </div>
  );
}

export function RoutePanel({
  activeRoute,
  originalRoute,
  approvedPlanLabel,
  className = '',
}: RoutePanelProps) {
  const route = activeRoute ?? originalRoute;

  if (!route) {
    return (
      <div className={clsx('rounded-2xl border border-gray-700 bg-gray-900/50 p-5', className)}>
        <h3 className="mb-4 text-sm font-semibold text-gray-300">ACTIVE ROUTE</h3>
        <p className="text-sm text-gray-500">No route data available</p>
      </div>
    );
  }

  return (
    <div className={clsx('rounded-2xl border border-gray-700 bg-gray-900/50 p-5', className)}>
      <h3 className="mb-4 flex flex-wrap items-center gap-2 text-sm font-semibold text-gray-300">
        <span className="h-2 w-2 rounded-full bg-blue-500" />
        ACTIVE ROUTE
        <span className="text-xs font-mono text-gray-500">({route.waypoints.length} waypoints)</span>
      </h3>
      {approvedPlanLabel && (
        <div className="mb-3 text-[10px] font-mono leading-relaxed text-gray-400">
          Approved plan: {approvedPlanLabel}
        </div>
      )}
      <div className="space-y-5">
        {route.waypoints.map((waypoint, index) => (
          <WaypointItem key={waypoint.id} waypoint={waypoint} index={index} />
        ))}
      </div>
    </div>
  );
}
