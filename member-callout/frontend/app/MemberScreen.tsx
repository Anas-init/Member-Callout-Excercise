"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";

type Message = {
  id: string; // the recipient row, which is what read/acknowledge act on
  title: string;
  body: string;
  needs_ack: boolean;
  sent_at: string | null;
  delivery_status: string;
  read_at: string | null;
  acknowledged_at: string | null;
};

function when(value: string | null) {
  return value ? new Date(value).toLocaleString() : null;
}

export default function MemberScreen({
  token,
  onSignOut,
}: {
  token: string;
  onSignOut: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const handleError = useCallback(
    (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) {
        onSignOut();
        return;
      }
      setError(err instanceof ApiError ? err.message : String(err));
    },
    [onSignOut],
  );

  // Polls so a callout sent from the leadership screen shows up here without a
  // refresh. Open the two screens side by side and you can watch it arrive.
  useEffect(() => {
    let stopped = false;
    const load = () =>
      api<{ results: Message[] }>("/api/members/announcements/", { token })
        .then((data) => {
          if (!stopped) {
            setMessages(data.results);
            setLoaded(true);
          }
        })
        .catch(handleError);
    load();
    const timer = setInterval(load, 5000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [token, handleError]);

  async function act(message: Message, action: "read" | "acknowledge") {
    setBusy(message.id + action);
    setError("");
    try {
      const updated = await api<Message>(
        `/api/members/announcements/${message.id}/${action}/`,
        { method: "POST", token, body: {} },
      );
      setMessages((current) =>
        current.map((row) => (row.id === updated.id ? updated : row)),
      );
    } catch (err) {
      handleError(err);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <h1>Your callouts</h1>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {loaded && messages.length === 0 && (
        <p>
          Nothing yet. When your local sends a callout it will appear here within a few
          seconds.
        </p>
      )}

      {messages.map((message) => {
        const readAt = when(message.read_at);
        const ackAt = when(message.acknowledged_at);
        return (
          <section
            key={message.id}
            style={{ border: "1px solid #999", padding: 12, marginBottom: 12 }}
          >
            <h2 style={{ margin: "0 0 6px" }}>{message.title}</h2>
            <p style={{ whiteSpace: "pre-wrap", margin: "0 0 8px" }}>{message.body}</p>
            <p style={{ margin: "0 0 8px" }}>
              <small>Sent {when(message.sent_at) ?? "just now"}</small>
            </p>

            <p style={{ margin: "0 0 8px" }}>
              {readAt ? <small>You read this on {readAt}</small> : <small>Unread</small>}
              {message.needs_ack && (
                <>
                  <br />
                  {ackAt ? (
                    <small>You confirmed you are coming on {ackAt}</small>
                  ) : (
                    <small>Your local is asking you to confirm you are coming</small>
                  )}
                </>
              )}
            </p>

            {!readAt && (
              <button
                onClick={() => act(message, "read")}
                disabled={busy !== ""}
              >
                {busy === message.id + "read" ? "Saving..." : "Mark as read"}
              </button>
            )}{" "}
            {message.needs_ack && !ackAt && (
              <button
                onClick={() => act(message, "acknowledge")}
                disabled={busy !== ""}
              >
                {busy === message.id + "acknowledge" ? "Saving..." : "I'll be there"}
              </button>
            )}
          </section>
        );
      })}
    </>
  );
}
