# Member Callout

A union leader writes one message, every member of their local gets it, and the
leader can see who has read it and who has said they're coming.

The thinking behind it is in [DESIGN.md](DESIGN.md)

## Run it

You need Docker Desktop running. Nothing else, no Python and no database setup.

But before doing that you need to add some env variables to get it running smoothly

```bash
cd member-callout
touch .env
```
Paste this exact content in .env file that you have created:

I have not added GEMINI_API_KEY which can not be pushed on github due to security scan and google revoke the api itself. So i have send the API_KEY with mail along with submission.
```bash
SECRET_KEY=+8_5pdl6)9__!!t99_xkc-2d8vdlu$#%mqru%vpx2hayf(kp8%

POSTGRES_PASSWORD=local-dev
GEMINI_API_KEY= paste that emailed key here
```

Then run

```bash
docker compose up --build
```

Give it about a minute. It builds the app, starts a database and two copies of
the backend behind a load balancer, and fills the database with test data. Once
you see `nginx ... Started`, open a second terminal for the web app:

```bash
cd member-callout/frontend
npm install
npm run dev
```

Now open http://localhost:3000.

Use `localhost:3000`, not `127.0.0.1:3000`. They look like the same thing but the
backend only trusts the first one, and the second will be blocked by your
browser.

To stop everything, press `Ctrl+C` in both terminals and run `docker compose
down`. Add `-v` if you also want to wipe the data.

## Sign in

Four accounts, all with the password `callout1234`:

| Local | Leader, who sends | Member, who receives |
|---|---|---|
| Local 27 (2,000 members) | `denise.okafor@local27.crewlink.test` | `ray.calderon@local27.crewlink.test` |
| Local 9 (200 members) | `walter.brennan@local9.crewlink.test` | `ray.calderon@local9.crewlink.test` |

The same sign-in page serves both. Leaders land on a page for writing and sending
a callout; members land on their own list of callouts.

## Try the whole thing

Open two browser windows side by side, one signed in as the leader and one as the
member. Then:

1. As the leader, write a title and a message and press Send. It comes back
   straight away, because the 1,961 messages go out in the background.
2. Watch the counts. "Sent to their phone" climbs from 0 to 1,961 over a few
   seconds as they are delivered.
3. Look at the member window. The callout turns up within about five seconds.
4. As the member, press "Mark as read", then "I'll be there".
5. Look back at the leader window. Within a few seconds "Read it" and "Confirmed
   they are coming" have each gone up by one.

Press either member button twice and nothing changes, the original time stays.
Press Send twice as the leader and only one callout goes out.

## Let it write the message for you

Leaders type in a hurry. On the leader's page, choose "Paste a messy note", drop
in something like:

```
emergency mtg thurs 6pm hall re: contractor pulling crews off the westside job,
EVERYONE needs to be there this is the third time
```

You get back a clear title, a message, and the short version that shows on a
phone. Nothing has been sent: at that point the callout has zero recipients. You
can edit any of it, and only "Approve and send" actually sends it. The database
itself refuses to send wording that nobody approved.

This works with no API key at all, falling back to a plain tidy-up of what you
typed, and the page tells you which one you got. 

## One local cannot see another local's data

Sign out and sign back in as the Local 9 member,
`ray.calderon@local9.crewlink.test`.

Then you will see no announcement because announcement was seeded for local 27 on docker startup which ensures rule 1 is enforced.

## Nobody gets the same callout twice

Pressing Send twice in the browser covers the everyday case: the second press
changes nothing.

The harder case cannot be done from a browser, because a browser can only click
once at a time. This is ten people pressing Send at the same instant, with the
requests landing on different copies of the backend. Sign in as a leader to get a
token from `POST http://localhost:8080/api/auth/login/`, then:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8080/api/announcements/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer PASTE_LEADER_TOKEN_HERE" \
    -d '{"idempotency_key":"22222222-2222-4222-8222-222222222222","title":"Rule 2 test","body":"Hall, Tuesday 7pm."}' &
done; wait; echo
```

```
201 200 200 200 200 200 200 200 200 200
```

One `201`, created once. Nine `200`s, each saying "already exists, sending
nothing". Wait ten seconds and count what actually went out:

```bash
docker compose exec db psql -U test -d assignment \
  -c "SELECT count(*) AS messaged, count(DISTINCT recipient_id) AS people FROM api_pushlog;"
```

Those two numbers come back equal, so nobody was messaged twice. It holds because
the database makes the call, not the app. The two backend copies never talk to
each other, and the copy that says "already exists" usually isn't the one that
created it.

## TEST ACCOUNTS

```json
{
  "web_app": "http://localhost:3000",
  "base_url": "http://localhost:8080",
  "password_for_every_account": "callout1234",
  "locals": {
    "local27": {
      "id": "7fea7241-c8cb-51c2-b951-e004cc350630",
      "name": "Local 27",
      "members": 2000,
      "leader": "denise.okafor@local27.crewlink.test",
      "member": "ray.calderon@local27.crewlink.test"
    },
    "local9": {
      "id": "ce651bfa-fc19-585f-b8cb-83f6139ce155",
      "name": "Local 9",
      "members": 200,
      "leader": "walter.brennan@local9.crewlink.test",
      "member": "ray.calderon@local9.crewlink.test"
    }
  },
  "existing_announcement_id": "5c4922ea-89c4-5696-8cc7-2024b3d83bd2",
  "existing_announcement_local": "local27",
  "local9_member_id": "fcfdf06b-7037-5a5b-93e4-43921b06fc0f",
  "auth": "Authorization: Bearer <access token from POST /api/auth/login/>",
  "endpoints": [
    { "method": "POST", "path": "/api/auth/login/", "auth": "none" },
    { "method": "GET",  "path": "/api/locals/", "auth": "leader", "note": "only the caller's own local" },
    { "method": "GET",  "path": "/api/announcements/", "auth": "leader" },
    { "method": "POST", "path": "/api/announcements/", "auth": "leader", "note": "idempotency_key + title + body sends now; idempotency_key + raw_text starts a draft" },
    { "method": "GET",  "path": "/api/announcements/{id}/", "auth": "leader", "note": "includes live sent/read/acknowledged counts" },
    { "method": "POST", "path": "/api/announcements/{id}/ai-draft/", "auth": "leader", "note": "messy note in, clean title/body/push_preview out, not sent" },
    { "method": "POST", "path": "/api/announcements/{id}/ai-draft/confirm/", "auth": "leader", "note": "human approval; only this can send an AI draft" },
    { "method": "GET",  "path": "/api/members/announcements/", "auth": "member", "note": "own inbox only" },
    { "method": "POST", "path": "/api/members/announcements/{recipient_id}/read/", "auth": "member" },
    { "method": "POST", "path": "/api/members/announcements/{recipient_id}/acknowledge/", "auth": "member" }
  ]
}
```

Those ids stay the same even if you wipe the data and start over, so they'll
always work.
