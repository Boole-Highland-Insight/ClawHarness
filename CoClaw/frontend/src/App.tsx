import { useEffect, useState } from 'react';

import { ContainerCard } from './components/ContainerCard';
import { Nav } from './components/Nav';
import { getDashboardData } from './services/harnessService';
import type { Container } from './types';

export function App() {
  const [containers, setContainers] = useState<Container[]>([]);

  useEffect(() => {
    getDashboardData().then(setContainers);
  }, []);

  return (
    <main className="page">
      <h1>CoClaw Dashboard</h1>
      <Nav />
      <section className="grid">
        {containers.map((container) => (
          <ContainerCard key={container.id} container={container} />
        ))}
      </section>
    </main>
  );
}
