const GENDER_LABELS: Record<string, string> = { M: "Male", F: "Female" };

export function voiceLabel(v: { name: string; gender?: string | null; language?: string | null }): string {
  const parts: string[] = [];
  const g = v.gender ? GENDER_LABELS[v.gender] : undefined;
  if (g) parts.push(g);
  if (v.language) parts.push(v.language);
  return parts.length > 0 ? `${v.name} (${parts.join(", ")})` : v.name;
}
