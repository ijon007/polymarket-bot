"use client";

import { ConvexClientProvider } from "@/components/convex-client";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ConvexClientProvider>
      {children}
    </ConvexClientProvider>
  );
}
