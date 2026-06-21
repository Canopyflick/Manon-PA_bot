# Google Calendar OAuth (Nathan)

Nathan's calendar tools use n8n credential **Google Calendar - n8n & Gemini Ben persoonlijk** (`googleCalendarOAuth2Api`).

## Why tokens keep dying (~7 days)

Google OAuth apps with **Publishing status: Testing** and **User type: External** issue refresh tokens that expire after **7 days**. n8n already refreshes short-lived access tokens automatically; when the **refresh token** is gone, you get:

```text
invalid_grant … refresh token is invalid, expired, revoked …
```

This is almost always the Testing-mode 7-day limit, not an n8n bug.

## Publish vs verification (you probably don't need verification)

Google conflates two things in the UI. For **personal Nathan use** (only you, `@gmail.com`), you need **Publish**, not **verification**.

| | **Publish app** | **Prepare for verification** |
| --- | --- | --- |
| Purpose | Move Testing → **In production**; stops 7-day refresh token expiry | Formal Google review for public apps |
| Required for Nathan? | **Yes** | **No** (personal-use exception) |
| What you get | Unverified production app; scary consent screen; long-lived tokens | Verified app; no warning screen; for apps open to anyone |

When you click **Publish app**, Google shows a popup listing verification requirements (privacy policy, demo video, domain verification, etc.). That is informational — **click Confirm anyway**. You are not committing to submit for verification.

**"Prepare for verification" greyed out** is normal and usually means one of:

1. **App still in Testing** — verification prep only unlocks *after* you publish (Google's own docs: publish first, then prepare).
2. **Verification not required** — check **Verification Center**; it may say verification isn't needed for your use case.
3. **Scopes not declared** — in the new UI: **Google Auth Platform** → **Data access** → **Add or remove scopes**. Add Calendar scopes there even if n8n already uses them. One forum user had a greyed-out button until scopes were added to Data access.
4. **You don't need the button** — Google's [personal use exception](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification#exceptions-to-verification-requirements) explicitly covers apps used only by you (or a few people you know). You accept the unverified-app screen yourself.

Calendar scopes (`…/auth/calendar`, `…/auth/calendar.events`) are **sensitive**, not **restricted** — so even *if* you verified later, there's no annual security assessment (that's for restricted scopes like Gmail full access).

### Recommended publish steps (personal app)

1. **Host privacy policy** on `bentenberge.com` (see `website` repo — `/privacy` route). Google requires:
   - **Application home page:** `https://bentenberge.com`
   - **Privacy policy link:** `https://bentenberge.com/privacy`
   - Footer on the homepage must link to the same privacy URL.
2. **Google Auth Platform** → **Branding** → **Authorized domains** → add `bentenberge.com` (covers `n8n.bentenberge.com` redirect URIs).
3. **Verify domain ownership** in [Google Search Console](https://search.google.com/search-console) for `bentenberge.com` if Google prompts (DNS TXT record via Cloudflare is typical).
4. **User type: External** → **Data access** → add Calendar scopes → **Publish app** → **Confirm** (verification optional for solo use).
5. Re-auth Nathan in n8n after publishing.

Calendar scopes to declare under **Data access**:

- `https://www.googleapis.com/auth/calendar`
- `https://www.googleapis.com/auth/calendar.events`

### If Publish itself is blocked

Fill missing required fields on the consent screen / branding page (often privacy policy + homepage). You do **not** need to complete verification to publish — only to remove the unverified warning for arbitrary Google users.

## Permanent fix (do once)
After publishing to **In production** (unverified is OK):

1. Confirm the OAuth client matches n8n (Client ID in credential settings).
2. Re-auth once so the new refresh token is issued under production policy.

OAuth client redirect URIs:

```text
https://n8n.bentenberge.com/rest/oauth2-credential/callback
```

For the local re-auth script, also add:

```text
http://127.0.0.1:8765/
```

## Re-auth when refresh token is dead

### Option A — n8n UI (quick)

1. Open `https://n8n.bentenberge.com` → **Credentials** → **Google Calendar - n8n & Gemini Ben persoonlijk**.
2. Click **Connect** / **Sign in with Google** and complete consent.
3. Save. Test Nathan in Telegram.

### Option B — script (stores refresh token in `.env`, updates n8n via API)

From repo root, with `ops/raspberry-pi/.env` filled (`GOOGLE_OAUTH_*`, `N8N_API_KEY`, optional `GOOGLE_CALENDAR_CREDENTIAL_ID`):

```powershell
.\ops\raspberry-pi\scripts\google-oauth-auth.ps1
```

The script opens a browser, listens on `http://127.0.0.1:8765/`, exchanges the code for tokens, PATCHes the n8n credential, and writes `GOOGLE_OAUTH_REFRESH_TOKEN` into `.env` for disaster recovery.

## What cannot be fully automated

Google requires browser consent to issue a **new** refresh token. No script or n8n workflow can silently re-authorize a consumer Gmail account without you clicking through Google once.

After the app is **In production**, you should not need to do this weekly.

## Alternative: service account (no OAuth expiry at all)

If publish/verify remains painful, n8n supports a **Google Service Account** credential for Calendar. Create a service account, download JSON, share your Google Calendar with the service account email (`…@….iam.gserviceaccount.com`) with "Make changes to events", and point Nathan's calendar nodes at that credential instead of OAuth. No refresh tokens, no consent screen. Trade-off: sharing calendar with a bot account; credential type change in the workflow.

Optional: Nathan Error Notifier already alerts on calendar failures; a scheduled "list events" health workflow can ping Manon before you notice in Telegram.

## Credential IDs

| Name | Type | ID (post-rebuild) |
| --- | --- | --- |
| Google Calendar - n8n & Gemini Ben persoonlijk | `googleCalendarOAuth2Api` | `Sc6NYYy2HJCpDM78` |

If the credential is recreated, update `GOOGLE_CALENDAR_CREDENTIAL_ID` in `.env`.
