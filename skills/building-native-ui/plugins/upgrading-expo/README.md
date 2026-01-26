# Expo SDK Upgrade Plugin

Helps Claude guide you through upgrading Expo SDK versions safely and efficiently.

## What This Plugin Does

- Walks through the step-by-step upgrade process (`npx expo install expo@latest`)
- Identifies deprecated packages and their modern replacements
- Cleans up outdated configuration (babel, metro, postcss)
- Handles cache clearing for both managed and bare workflows
- Knows about breaking changes between SDK versions

## When to Use

- Upgrading to a new Expo SDK version
- Fixing dependency conflicts after an upgrade
- Migrating from deprecated packages (expo-av → expo-audio/expo-video)
- Cleaning up legacy configuration files

## License

MIT
