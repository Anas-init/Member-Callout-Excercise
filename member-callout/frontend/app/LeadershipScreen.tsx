"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";

const PREVIEW_MAX = 120;

type Counts = { total: number; sent: number; read: number; acknowledged: number };
type Detail = { id: string; title: string; status: string; counts: Counts };
type Draft = { title?: string; body?: string; push_preview?: string; source?: string };

export default function LeadershipScreen({
  token,
  onSignOut,
}: {
  token: string;
  onSignOut: () => void;
}) {
  const [localName, setLocalName] = useState("");

  const [mode, setMode] = useState<"manual" | "ai">("manual");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [needsAck, setNeedsAck] = useState(true);
  const [rawText, setRawText] = useState("");

  // Made once when the form loads, NOT when Send is pressed. A new key per click
  // would turn a double-click into two callouts and defeat the server's
  // duplicate protection from the client side.
  const [idempotencyKey, setIdempotencyKey] = useState("");

  const [draftId, setDraftId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);

  const [announcementId, setAnnouncementId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);

  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

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

  useEffect(() => {
    setIdempotencyKey(crypto.randomUUID());
  }, []);

  useEffect(() => {
    api<{ results: { name: string }[] }>("/api/locals/", { token })
      .then((data) => setLocalName(data.results[0]?.name ?? ""))
      .catch(handleError);
  }, [token, handleError]);

  // Counts are cached server-side for 2 seconds, so polling faster gains
  // nothing. Polling continues after the status reaches "sent" because read and
  // acknowledged keep moving as members open the message.
  useEffect(() => {
    if (!announcementId) return;
    let stopped = false;
    const load = () =>
      api<Detail>(`/api/announcements/${announcementId}/`, { token })
        .then((data) => {
          if (!stopped) setDetail(data);
        })
        .catch(handleError);
    load();
    const timer = setInterval(load, 3000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [token, announcementId, handleError]);

  const resetComposer = useCallback(() => {
    setTitle("");
    setBody("");
    setRawText("");
    setDraft(null);
    setDraftId(null);
    setIdempotencyKey(crypto.randomUUID());
  }, []);

  async function sendNow(event: React.FormEvent) {
    event.preventDefault();
    setBusy("send");
    setError("");
    setNotice("");
    try {
      const created = await api<{ id: string }>("/api/announcements/", {
        method: "POST",
        token,
        body: { idempotency_key: idempotencyKey, title, body, needs_ack: needsAck },
      });
      setAnnouncementId(created.id);
      resetComposer();
    } catch (err) {
      // A 404 here means this key already belongs to someone else's callout.
      if (err instanceof ApiError && err.status === 404) {
        setIdempotencyKey(crypto.randomUUID());
        setError("That send key was already in use. A fresh one is ready, press Send again.");
      } else {
        handleError(err);
      }
    } finally {
      setBusy("");
    }
  }

  async function writeItUp(event: React.FormEvent) {
    event.preventDefault();
    setBusy("draft");
    setError("");
    setNotice("");
    try {
      // Creating with raw_text makes a draft. It has no recipients and cannot go
      // out until a person approves it below.
      const id =
        draftId ??
        (
          await api<{ id: string }>("/api/announcements/", {
            method: "POST",
            token,
            body: {
              idempotency_key: idempotencyKey,
              raw_text: rawText,
              needs_ack: needsAck,
            },
          })
        ).id;
      setDraftId(id);

      const result = await api<{ ai_draft: Draft }>(`/api/announcements/${id}/ai-draft/`, {
        method: "POST",
        token,
        body: {},
      });
      setDraft(result.ai_draft);
    } catch (err) {
      handleError(err);
    } finally {
      setBusy("");
    }
  }

  async function approveAndSend() {
    if (!draftId || !draft) return;
    setBusy("approve");
    setError("");
    setNotice("");
    try {
      const sent = await api<{ id: string }>(`/api/announcements/${draftId}/ai-draft/confirm/`, {
        method: "POST",
        token,
        body: { title: draft.title, body: draft.body, push_preview: draft.push_preview },
      });
      setAnnouncementId(sent.id);
      resetComposer();
    } catch (err) {
      // Already approved: an earlier click got there first. That is the duplicate
      // protection working, so show the counts rather than an error.
      if (err instanceof ApiError && err.status === 409) {
        setAnnouncementId(draftId);
        setNotice("This callout had already been approved, so it was not sent twice.");
        resetComposer();
      } else {
        handleError(err);
      }
    } finally {
      setBusy("");
    }
  }

  const counts = detail?.counts;

  return (
    <>
      <h1>Send a callout</h1>

      <p>
        <label>
          Local<br />
          <select value={localName} disabled>
            <option>{localName || "loading..."}</option>
          </select>
        </label>
        <br />
        <small>
          Your local is the only one listed. Leadership can only ever send to their own
          members.
        </small>
      </p>

      {!draft && (
        <>
          <p>
            <label>
              <input
                type="radio"
                checked={mode === "manual"}
                onChange={() => setMode("manual")}
              />{" "}
              Write it myself
            </label>{" "}
            <label>
              <input type="radio" checked={mode === "ai"} onChange={() => setMode("ai")} />{" "}
              Paste a messy note and have it written up
            </label>
          </p>
          <p>
            <label>
              <input
                type="checkbox"
                checked={needsAck}
                onChange={(e) => setNeedsAck(e.target.checked)}
              />{" "}
              Ask members to confirm they are coming
            </label>
          </p>
        </>
      )}

      {!draft && mode === "manual" && (
        <form onSubmit={sendNow}>
          <p>
            <label>
              Title<br />
              <input value={title} onChange={(e) => setTitle(e.target.value)} size={60} required />
            </label>
          </p>
          <p>
            <label>
              Message<br />
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                rows={4}
                cols={60}
                required
              />
            </label>
          </p>
          <button disabled={busy !== ""}>{busy === "send" ? "Sending..." : "Send"}</button>
        </form>
      )}

      {!draft && mode === "ai" && (
        <form onSubmit={writeItUp}>
          <p>
            <label>
              Your note, however you type it<br />
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                rows={4}
                cols={60}
                required
                placeholder="emergency mtg thurs 6pm hall re: contractor pulling crews off the westside job"
              />
            </label>
          </p>
          <button disabled={busy !== ""}>
            {busy === "draft" ? "Writing it up, this can take a few seconds..." : "Write it up"}
          </button>
          <br />
          <small>Nothing is sent yet. You will see a draft to approve first.</small>
        </form>
      )}

      {draft && (
        <section>
          <h2>Check this before it goes out</h2>
          <p>
            <small>
              Written by {draft.source === "llm" ? "the AI" : "a plain tidy-up (AI unavailable)"}.
              Nobody has received this yet. Edit anything you want to change.
            </small>
          </p>
          <p>
            <label>
              Title<br />
              <input
                value={draft.title ?? ""}
                onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                size={60}
              />
            </label>
          </p>
          <p>
            <label>
              Message<br />
              <textarea
                value={draft.body ?? ""}
                onChange={(e) => setDraft({ ...draft, body: e.target.value })}
                rows={4}
                cols={60}
              />
            </label>
          </p>
          <p>
            <label>
              Phone notification<br />
              <input
                value={draft.push_preview ?? ""}
                onChange={(e) => setDraft({ ...draft, push_preview: e.target.value })}
                size={60}
              />
            </label>
            <br />
            <small>
              {(draft.push_preview ?? "").length} of {PREVIEW_MAX} characters
            </small>
          </p>
          <button onClick={approveAndSend} disabled={busy !== ""}>
            {busy === "approve" ? "Sending..." : "Approve and send"}
          </button>{" "}
          <button onClick={writeItUp} disabled={busy !== ""}>
            {busy === "draft" ? "Rewriting..." : "Write it again"}
          </button>{" "}
          <button onClick={resetComposer} disabled={busy !== ""}>
            Discard
          </button>
        </section>
      )}

      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {notice && <p style={{ color: "darkorange" }}>{notice}</p>}

      {announcementId && (
        <section>
          <h2>Who has seen it</h2>
          <p>
            <strong>{detail?.title}</strong>
            <br />
            <small>Status: {detail?.status ?? "loading..."} (refreshing every 3 seconds)</small>
          </p>
          <table border={1} cellPadding={6}>
            <tbody>
              <tr>
                <td>Members it went to</td>
                <td align="right">{counts?.total ?? "-"}</td>
              </tr>
              <tr>
                <td>Sent to their phone</td>
                <td align="right">{counts?.sent ?? "-"}</td>
              </tr>
              <tr>
                <td>Read it</td>
                <td align="right">{counts?.read ?? "-"}</td>
              </tr>
              <tr>
                <td>Confirmed they are coming</td>
                <td align="right">{counts?.acknowledged ?? "-"}</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}
