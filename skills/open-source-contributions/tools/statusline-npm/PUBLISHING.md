# Publishing contextbricks to npm

## Prerequisites

1. npm account with publish access to `contextbricks` package
2. Granular access token with:
   - **Read and write access** to all packages
   - **Bypass two-factor authentication (2FA)** enabled

## Create Access Token (One-time Setup)

1. Go to https://www.npmjs.com/settings/tokens
2. Click **Generate New Token** → **Granular Access Token**
3. Configure:
   - **Token name**: `claude code` (or similar)
   - **Expiration**: 90 days (or your preference)
   - **Packages and scopes**: Read and write access to all packages
   - **Security settings**: ✅ Bypass two-factor authentication (2FA)
4. Copy the token (starts with `npm_...`)

## Publishing

### Option 1: Set Token and Publish (Recommended)

```bash
# Set the auth token
npm config set //registry.npmjs.org/:_authToken=npm_YOUR_TOKEN_HERE

# Publish
cd /home/jez/Documents/claude-skills/tools/statusline-npm
npm publish
```

### Option 2: One-liner

```bash
npm config set //registry.npmjs.org/:_authToken=npm_YOUR_TOKEN_HERE && cd /home/jez/Documents/claude-skills/tools/statusline-npm && npm publish
```

## Version Bumping

Before publishing a new version:

1. Update `package.json` version:
   ```bash
   # Patch (1.0.4 → 1.0.5)
   npm version patch

   # Minor (1.0.4 → 1.1.0)
   npm version minor

   # Major (1.0.4 → 2.0.0)
   npm version major
   ```

2. Or manually edit `package.json`:
   ```json
   "version": "2.0.0"
   ```

## Checklist Before Publishing

- [ ] Both `statusline.sh` files are in sync:
  - `tools/statusline/statusline.sh`
  - `tools/statusline-npm/scripts/statusline.sh`
- [ ] README.md updated with changelog
- [ ] Version bumped in `package.json`
- [ ] Tested locally with mock JSON data
- [ ] Git committed and pushed

## Verify Publication

```bash
# Check published version
npm view contextbricks version

# Test installation
npx contextbricks@latest --version
```

## Troubleshooting

### "Two-factor authentication required"

Your token doesn't have "Bypass 2FA" enabled. Create a new token with that option checked.

### "403 Forbidden"

- Token expired (check expiration date on npmjs.com)
- Token doesn't have write access
- Not logged in as package owner

### "E404 Not Found" on first publish

The package name might be taken. Check https://www.npmjs.com/package/contextbricks

## Token Security

- Tokens are stored in `~/.npmrc`
- Don't commit tokens to git
- Rotate tokens periodically
- Delete unused tokens at https://www.npmjs.com/settings/tokens
