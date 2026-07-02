# Copilot CLI — Google Docs Read/Write Setup & Authentication

> Source: `#Support Agent` Slack thread — question from `virai`

## Question

How to read and write Google Docs using Copilot CLI? How to set up proper
authentication? (Claude CLI works fine.)

## Answer

For Copilot CLI, Google Docs read/write should go through **Captain MCP** (not a
native Copilot CLI Google Docs integration). Since Claude CLI works, you likely
already have a valid Captain/Google OAuth setup for Claude, but Copilot may not
have Captain MCP registered.

### 1. Make sure GitHub auth is healthy for Copilot CLI

```bash
gh auth login -h github.com -p https -w

# macOS credential helper
git config --global credential.helper osxkeychain
```

### 2. Register Captain MCP + LinkedIn marketplace for Copilot CLI

```bash
captain setup --copilot
```

### 3. Start Copilot CLI and verify

```
/mcp
/plugin
```

You should see Captain listed under MCP, and the LinkedIn plugin
marketplace/plugins available.

### 4. Reduce repeated prompts (optional)

To reduce repeated prompts, you can launch with Captain pre-approved:

```bash
copilot --allow-tool='captain'
```

### 5. Google OAuth flow

For Google Docs access, Captain should trigger a Google OAuth browser flow the
first time Copilot tries to use the Google Docs capability. Complete that
browser auth flow, then ask Copilot something like:

```
Read this Google Doc: <doc URL>
```

or

```
Create/update a Google Doc with the following content...
```

### 6. Remote host / rdev / SSH environments

If you are on a remote host / rdev / SSH environment, use the headless setup
flow:

```bash
captain setup agent-platform --headless
```

Then paste the auth code back when prompted.

### 7. If Copilot CLI still doesn't show Captain / marketplace looks stale

Reset the local marketplace cache and rerun setup:

```bash
rm -rf ~/Library/Caches/copilot/marketplaces/linkedin-multiproduct-li-productivity-agents
captain setup --copilot
```

## References

- [Copilot CLI installation docs](https://upgraded-carnival-jn7vzqr.pages.github.io/docs/copilot-cli/installation.html)
- [Copilot CLI tips](https://upgraded-carnival-jn7vzqr.pages.github.io/docs/copilot-cli/copilot-cli-tips-and-tricks.html)

## Troubleshooting

If it still fails, share the exact Copilot CLI error or what `/mcp` shows for
further troubleshooting or to create a Copilot CLI support ticket.
