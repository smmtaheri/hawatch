import type { CSSProperties, HTMLAttributes } from "react";

export const GEAR_ICON_NAMES = [
  "waterproof-shell",
  "insulated-jacket",
  "base-layer",
  "hiking-boots",
  "trekking-poles",
  "backpack",
  "gloves",
  "beanie",
  "sunglasses",
  "headlamp",
  "water-bottle",
  "energy-snack",
  "sunscreen",
  "first-aid",
  "emergency-blanket",
  "compass",
  "power-bank",
  "gaiters",
  "microspikes",
  "whistle",
] as const;

export type GearIconName = (typeof GEAR_ICON_NAMES)[number];

function isGearIconName(value: string): value is GearIconName {
  return (GEAR_ICON_NAMES as readonly string[]).includes(value);
}

export function GearIcon({
  name,
  size = 30,
  title,
  className,
  style,
  ...props
}: {
  name: string;
  size?: number;
  title?: string;
  className?: string;
  style?: CSSProperties;
} & Omit<HTMLAttributes<HTMLSpanElement>, "aria-label" | "title">) {
  if (!isGearIconName(name)) return null;

  return (
    <span
      {...props}
      className={className ? `hawatch-gear-icon ${className}` : "hawatch-gear-icon"}
      style={{
        ...style,
        width: size,
        height: size,
        "--hawatch-gear-url": `url("/icons/gear/${name}.svg")`,
      } as CSSProperties}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    />
  );
}
