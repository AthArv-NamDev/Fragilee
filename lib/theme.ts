export const THEMES = ["light", "dark"] as const;
export type ThemeName = (typeof THEMES)[number];

export function validTheme(value: string | undefined | null): ThemeName {
  return THEMES.includes(value as ThemeName) ? (value as ThemeName) : "dark";
}

export const THEME_LABELS: Record<ThemeName, string> = {
  light: "Light",
  dark: "Dark",
};
