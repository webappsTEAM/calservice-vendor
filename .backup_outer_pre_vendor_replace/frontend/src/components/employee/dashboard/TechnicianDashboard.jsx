import React from 'react';
import { TechnicianCockpit } from './TechnicianCockpit.jsx';

/**
 * TechnicianDashboard.jsx
 *
 * Modern operational cockpit for field service technicians.
 * Rebuilt from scratch with state-driven UI, real-time presence radar,
 * live shift timer, and step-by-step job progress stepper.
 */
export function TechnicianDashboard(props) {
  return <TechnicianCockpit {...props} />;
}

export default TechnicianDashboard;
