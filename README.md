# Member Callout

A union leader writes one message, every member of their local gets it, and the
leader can see who has read it and who has said they're coming.

The thinking behind it is in [DESIGN.md](DESIGN.md)

## Run it

You need Docker Desktop running. Nothing else, no Python and no database setup.

```bash
cd member-callout
docker compose up --build
```

Give it about a minute. It builds the app, starts a database and two copies of
the backend behind a load balancer, and fills the database with test data. Once
you see `nginx ... Started` it's ready at http://localhost:8080.

To stop it, press `Ctrl+C` and run `docker compose down`. Add `-v` if you also
want to wipe the data.

## Using these commands

Everything below is plain curl, so you can use it either way:

* In Postman, click Import, then Raw text, paste the command, and click Continue.
  You'll get a request you can press Send on.
* In a terminal. On Windows use Git Bash rather than PowerShell.

Anywhere you see `PASTE_TOKEN_HERE`, swap in the `access` value you got from
logging in. Nothing else needs changing. The ids below are real and they don't
change between restarts.

## Log in

There are four accounts and they all use the password `callout1234`:

| Local | Leader | Member |
|---|---|---|
| Local 27 (2,000 members) | `denise.okafor@local27.crewlink.test` | `ray.calderon@local27.crewlink.test` |
| Local 9 (200 members) | `walter.brennan@local9.crewlink.test` | `ray.calderon@local9.crewlink.test` |

```bash
curl -X POST http://localhost:8080/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"denise.okafor@local27.crewlink.test","password":"callout1234"}'
```

Look for `"access": "eyJ..."` in the reply and copy that long string. That's your
token, and every request below needs it.

## Send a callout

This comes back straight away. The 1,961 messages go out in the background so
nobody sits waiting at the keyboard.

```bash
curl -X POST http://localhost:8080/api/announcements/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer PASTE_LEADER_TOKEN_HERE" \
  -d '{"idempotency_key":"11111111-1111-4111-8111-111111111111","title":"Safety stand-down Friday","body":"All crews at the hall 7am Friday.","needs_ack":true}'
```

You'll get a `201` back along with an `id`. Now press Send a second time. You get
a `200` and the same announcement, and nothing goes out again. That's the
double-click protection, and you can watch it work just by clicking twice.

Copy the `id`, wait about ten seconds, then check the counts:

```bash
curl http://localhost:8080/api/announcements/PASTE_ANNOUNCEMENT_ID_HERE/ \
  -H "Authorization: Bearer PASTE_LEADER_TOKEN_HERE"
```

```json
"counts": { "total": 1961, "sent": 1961, "read": 0, "acknowledged": 0 }
```

## Read it as a member

Log in again, this time as `ray.calderon@local27.crewlink.test`, and open that
member's inbox:

```bash
curl http://localhost:8080/api/members/announcements/ \
  -H "Authorization: Bearer PASTE_MEMBER_TOKEN_HERE"
```

Copy the `id` of the first message. That's the recipient id, and it goes here:

```bash
curl -X POST http://localhost:8080/api/members/announcements/PASTE_RECIPIENT_ID_HERE/read/ \
  -H "Authorization: Bearer PASTE_MEMBER_TOKEN_HERE"
```

```bash
curl -X POST http://localhost:8080/api/members/announcements/PASTE_RECIPIENT_ID_HERE/acknowledge/ \
  -H "Authorization: Bearer PASTE_MEMBER_TOKEN_HERE"
```

Go back to the leader's counts and they'll read `"read": 1, "acknowledged": 1`.
If you press either one twice, you get the original timestamp back and nothing
changes.

## One local can't see another local's data

Log in as the Local 9 leader, then try to open a Local 27 announcement:

```bash
curl -i http://localhost:8080/api/announcements/5c4922ea-89c4-5696-8cc7-2024b3d83bd2/ \
  -H "Authorization: Bearer PASTE_LOCAL9_LEADER_TOKEN_HERE"
```

```
HTTP/1.1 404 Not Found
{"detail":"No Announcement matches the given query."}
```

You get a 404 rather than a 403, and that's deliberate. Saying "forbidden" would
confirm the announcement exists. "Not found" gives an outsider nothing.

## Nobody gets the same callout twice

Pressing Send twice covers the retry case. The harder one is ten people pressing
Send at the same moment, with the requests landing on different copies of the
backend. Postman sends one request at a time, so this bit needs a terminal:

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

One `201`, so it was created once. Nine `200`s, each of them saying "already
exists, sending nothing". Wait ten seconds and count what actually went out:

```bash
docker compose exec db psql -U test -d assignment \
  -c "SELECT count(*) AS messaged, count(DISTINCT recipient_id) AS people FROM api_pushlog;"
```

`messaged` and `people` come back equal, so nobody was messaged twice.

The reason this holds is that the database makes the call, not the app. The two
backend copies never talk to each other, and the copy that says "already exists"
usually isn't the one that created it.

## Turning a messy note into a clear callout

Leaders type in a hurry. You can send the raw note and the system will write it
up, but it can't go out until a person approves it.

First, start a draft from the messy note:

```bash
curl -X POST http://localhost:8080/api/announcements/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer PASTE_LEADER_TOKEN_HERE" \
  -d '{"idempotency_key":"33333333-3333-4333-8333-333333333333","raw_text":"emergency mtg thurs 6pm hall re: contractor pulling crews off the westside job, EVERYONE needs to be there this is the third time"}'
```

Then write it up, using the `id` you just got back:

```bash
curl -X POST http://localhost:8080/api/announcements/PASTE_ANNOUNCEMENT_ID_HERE/ai-draft/ \
  -H "Authorization: Bearer PASTE_LEADER_TOKEN_HERE"
```

You'll get a clear title, a body, a push preview under 120 characters, and
`"approved": false`. Nothing has been sent. At this point the message has zero
recipients.

Approving it is the only thing that sends it:

```bash
curl -X POST http://localhost:8080/api/announcements/PASTE_ANNOUNCEMENT_ID_HERE/ai-draft/confirm/ \
  -H "Authorization: Bearer PASTE_LEADER_TOKEN_HERE"
```

The database itself refuses to send wording that nobody approved, so it isn't
only the app doing the checking.

All of this works with no API key at all. Without one it falls back to a plain
tidy-up of whatever was typed. If you want the full version, get a free key from
[Google AI Studio](https://aistudio.google.com/apikey) and put it in
`member-callout/.env` as `GEMINI_API_KEY=`. If the provider is slow or down, the
leader still gets a usable draft instead of an error.

## Making Postman less tedious

Two shortcuts once you've imported a few requests.

To stop pasting tokens, add a collection variable called `token`. On the login
request, open Scripts, then Post-response, and add:

```javascript
pm.collectionVariables.set("token", pm.response.json().access);
```

Now use `Authorization: Bearer {{token}}` everywhere, and logging in keeps it up
to date on its own.

The `idempotency_key` values above are fixed so you can see the duplicate
protection working. When you want to send a genuinely new announcement instead,
put Postman's built-in `{{$guid}}` in that field.

## TEST ACCOUNTS

```json
{
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
