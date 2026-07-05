import { Fragment } from "react";

function inlineParts(text) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1, -1)}</code>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={index}>{part.slice(1, -1)}</em>;
    return <Fragment key={index}>{part}</Fragment>;
  });
}

/** Small, dependency-free renderer for the safe Markdown subset produced by case tools. */
export default function FormattedText({ text, className = "" }) {
  const normalized = String(text || "")
    .replace(/\s+(#{1,4}\s+)/g, "\n$1")
    .replace(/\s+([*-]\s+\*\*)/g, "\n$1")
    .trim();
  const lines = normalized.split(/\n+/).map((line) => line.trim()).filter(Boolean);

  return <div className={`formatted-text ${className}`.trim()}>
    {lines.map((line, index) => {
      const heading = line.match(/^(#{1,4})\s+(.+)$/);
      if (heading) return <h4 key={index}>{inlineParts(heading[2])}</h4>;
      const bullet = line.match(/^[*-]\s+(.+)$/);
      if (bullet) return <div className="formatted-bullet" key={index}><span>•</span><p>{inlineParts(bullet[1])}</p></div>;
      return <p key={index}>{inlineParts(line)}</p>;
    })}
  </div>;
}
