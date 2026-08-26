import type { ReactNode } from "react";
import { Header } from "./Header";

export function AppShell({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <main className={className}>
      <Header />
      {children}
    </main>
  );
}
