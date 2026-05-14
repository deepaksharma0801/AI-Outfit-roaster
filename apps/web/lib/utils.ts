import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function scoreLabel(score: number) {
  if (score >= 9) return "Runway felony";
  if (score >= 8) return "Certified drip";
  if (score >= 7) return "Solid fit";
  if (score >= 5.5) return "Needs styling";
  return "Closet reboot";
}
