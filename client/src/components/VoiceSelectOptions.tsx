import { SelectGroup, SelectItem, SelectLabel, SelectSeparator } from "@/components/ui/select";

interface Opt {
  value: string;
  label: string;
}

interface Props {
  opts: Opt[];
  favoriteIds: Set<string>;
  /** Optional items to prepend before the grouped list (e.g. "Use narrator default") */
  prepend?: React.ReactNode;
}

function isFavorite(value: string, favoriteIds: Set<string>): boolean {
  return value.startsWith("library:") && favoriteIds.has(value.slice(8));
}

export function VoiceSelectOptions({ opts, favoriteIds, prepend }: Props) {
  const favorites = opts.filter((o) => isFavorite(o.value, favoriteIds));
  const rest = opts.filter((o) => !isFavorite(o.value, favoriteIds));
  const hasGroups = favorites.length > 0;

  if (!hasGroups) {
    return (
      <>
        {prepend}
        {opts.map((o) => (
          <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
        ))}
      </>
    );
  }

  return (
    <>
      {prepend}
      <SelectGroup>
        <SelectLabel>Favorites</SelectLabel>
        {favorites.map((o) => (
          <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
        ))}
      </SelectGroup>
      <SelectSeparator />
      <SelectGroup>
        <SelectLabel>All Voices</SelectLabel>
        {rest.map((o) => (
          <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
        ))}
      </SelectGroup>
    </>
  );
}
