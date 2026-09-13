"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api, clearToken, decodeJwt, getToken, setToken } from "@/lib/api";
import LeadershipScreen from "./LeadershipScreen";
import MemberScreen from "./MemberScreen";

type Account = { full_name: string; role: string };

function LoginForm({ onDone }: { onDone: (token: string) => void }) {
  const [email, setEmail] = useState("denise.okafor@local27.crewlink.test");
  const [password, setPassword] = useState("callout1234");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api<{ access: string }>("/api/auth/login/", {
        method: "POST",
        body: { email, password },
      });
      setToken(data.access);
      onDone(data.access);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <h1>CrewLink</h1>
      <p>Sign in. Leaders send callouts, members read them.</p>
      <p>
        <label>
          Email<br />
          <input value={email} onChange={(e) => setEmail(e.target.value)} size={45} />
        </label>
      </p>
      <p>
        <label>
          Password<br />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            size={45}
          />
        </label>
      </p>
      <button disabled={busy}>{busy ? "Signing in..." : "Sign in"}</button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <p>
        <small>
          Try <code>denise.okafor@local27.crewlink.test</code> to send, or{" "}
          <code>ray.calderon@local27.crewlink.test</code> to receive. Password{" "}
          <code>callout1234</code> for both.
        </small>
      </p>
    </form>
  );
}

export default function Home() {
  const [token, setTokenState] = useState<string | null>(null);
  const [account, setAccount] = useState<Account | null>(null);

  const signOut = useCallback(() => {
    clearToken();
    setTokenState(null);
    setAccount(null);
  }, []);

  useEffect(() => {
    const stored = getToken();
    if (stored) setTokenState(stored);
  }, []);

  // The login response is only a token, so the name and role come from the
  // claims inside it rather than a separate request.
  useEffect(() => {
    if (!token) {
      setAccount(null);
      return;
    }
    setAccount(decodeJwt(token) as unknown as Account);
  }, [token]);

  const page = { padding: 24, maxWidth: 760, fontFamily: "system-ui, sans-serif" };

  if (!token || !account) {
    return (
      <main style={page}>
        <LoginForm onDone={setTokenState} />
      </main>
    );
  }

  return (
    <main style={page}>
      <p>
        Signed in as <strong>{account.full_name}</strong> ({account.role}){" "}
        <button onClick={signOut}>Sign out</button>
      </p>
      {account.role === "leader" ? (
        <LeadershipScreen token={token} onSignOut={signOut} />
      ) : (
        <MemberScreen token={token} onSignOut={signOut} />
      )}
    </main>
  );
}
