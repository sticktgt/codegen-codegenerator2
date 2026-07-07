import React from 'react';
import { routes } from './routes/routeRegistry.js';

export default function App() {
  const firstRoute = routes[0];
  const Screen = firstRoute?.component;

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: '24px' }}>
      <h1>Generated Prototype</h1>
      {Screen ? <Screen /> : <p>No screens have been generated yet.</p>}
    </main>
  );
}
