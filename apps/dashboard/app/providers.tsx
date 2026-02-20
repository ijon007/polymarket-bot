"use client";

import { ConvexClientProvider } from "@/components/convex-client";
import { DataModeProvider } from "@/lib/data-mode-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ConvexClientProvider>
      <DataModeProvider>{children}</DataModeProvider>
    </ConvexClientProvider>
  );
}
