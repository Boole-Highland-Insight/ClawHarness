const entries = ['Overview', 'Sessions', 'Cron', 'Tools', 'Models', 'Health', 'Raw Events'];

export function Nav() {
  return (
    <nav className="nav">
      {entries.map((entry) => (
        <button className="nav-item" key={entry} type="button">
          {entry}
        </button>
      ))}
    </nav>
  );
}
