import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // This app is the workspace root. Without this, Next walks up and finds an
  // unrelated package-lock.json in the home directory and warns about it.
  turbopack: { root: __dirname },

  // Don't generate AGENTS.md / CLAUDE.md on every dev start; they are tooling
  // scaffolding, not part of this submission.
  agentRules: false,
};

export default nextConfig;
