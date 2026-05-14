import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function scoreLabel(score: number) {
  if (score >= 9) return "Dangerous levels of drip";
  if (score >= 8) return "Certified, annoyingly";
  if (score >= 7) return "Low-key valid";
  if (score >= 6) return "Recoverable";
  if (score >= 4) return "NPC laundry day";
  return "Wardrobe crime scene";
}
