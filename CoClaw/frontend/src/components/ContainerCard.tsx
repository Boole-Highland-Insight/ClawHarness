import type { Container } from '../types';

function statusClass(status: string): string {
  return `status status-${status}`;
}

export function ContainerCard({ container }: { container: Container }) {
  return (
    <article className="container-card">
      <header className="container-head">
        <h3>{container.name}</h3>
        <span className={statusClass(container.status)}>{container.status}</span>
      </header>
      <p className="container-meta">{container.image}</p>
      <ul className="instance-list">
        {container.instances.map((instance) => (
          <li key={instance.id} className="instance-item">
            <div>
              <strong>{instance.name}</strong>
              <span className="instance-endpoint">{instance.endpoint ?? 'N/A'}</span>
            </div>
            <span className={statusClass(instance.status)}>{instance.status}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}
