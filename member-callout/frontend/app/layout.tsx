import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CrewLink Leadership",
  description: "Send a callout to your local and see who has read it",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
