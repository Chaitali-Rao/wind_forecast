export default function Stat({ label, value, unit, note }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}{unit && <span className="unit"> {unit}</span>}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  );
}
