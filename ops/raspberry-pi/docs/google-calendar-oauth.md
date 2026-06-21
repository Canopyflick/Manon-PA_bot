# Google Calendar OAuth (Nathan)

Nathan's calendar tools use n8n credential **Google Calendar - n8n & Gemini Ben persoonlijk** (`googleCalendarOAuth2Api`).

## Why tokens keep dying (~7 days)

Google OAuth apps with **Publishing status: Testing** and **User type: External** issue refresh tokens that expire after **7 days**. n8n already refreshes short-lived access tokens automatically; when the **refresh token** is gone, you get:

```text
invalid_grant … refresh token is invalid, expired, revoked …
```

This is almost always the Testing-mode 7-day limit, not an n8n bug.

## Permanent fix (do once)

In [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **OAuth consent screen**:

1. Confirm the app uses the same OAuth client as n8n (Client ID in credential settings).
2. Add your Google account under **Test users** if still in Testing (only needed while Testing).
3. Click **Publish app** → set **Publishing status** to **In production**.

For a personal `@gmail.com` calendar app (single user, Ben only):

- Calendar scopes are "sensitive" — Google may show an "unverified app" screen. You can still authorize your own account.
- After publishing, refresh tokens no longer expire on a 7-day timer (they remain valid until revoked, password change with Gmail scopes, 6 months unused, etc.).

Keep the OAuth client redirect URI that n8n uses:

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

After the app is **In production**, you should not need to do this weekly. Optional: Nathan Error Notifier already alerts on calendar failures; a scheduled "list events" health workflow can ping Manon before you notice in Telegram.

## Credential IDs

| Name | Type | ID (post-rebuild) |
| --- | --- | --- |
| Google Calendar - n8n & Gemini Ben persoonlijk | `googleCalendarOAuth2Api` | `Sc6NYYy2HJCpDM78` |

If the credential is recreated, update `GOOGLE_CALENDAR_CREDENTIAL_ID` in `.env`.
