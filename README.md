# Host for Android

This folder turns Host into a full-screen Android app. GitHub builds the APK for you in the cloud,
so you don't need Android Studio.

## Build it (about 5 minutes the first time)

1. Create a new **private** repository on GitHub (for example `host-game`).
2. Upload everything in this folder to it, keeping the folders as they are
   (including the hidden `.github` folder). The easiest way:
   ```
   git init
   git add .
   git commit -m "Host Android app"
   git branch -M main
   git remote add origin https://github.com/<you>/host-game.git
   git push -u origin main
   ```
3. Open the repo's **Actions** tab. The "Build Android APK" job starts by itself. Wait for the green check.
4. Open the repo's **Releases** (right side of the repo page). The newest release has `Host.apk`.

## Install it on your phone

1. On your phone, sign in to GitHub in the browser, open the newest release, and tap `Host.apk`.
2. Android asks to allow installs from your browser the first time. Allow it, then tap Install.
3. Open Host. It runs full screen with the status and navigation bars hidden.
   Swipe in from an edge to see them for a moment.

Your progress is saved inside the app. Uninstalling the app deletes it.

## Updating the game

Replace `www/index.html` with the newest `host.html`, then commit and push.
A new release with a fresh `Host.apk` appears a few minutes later. Install it over the old one;
your progress is kept because the app ID stays the same (`com.hostgame.app`).

## In-app updates

The app checks GitHub for a newer release when it starts and every 6 hours. When there is one, the main menu
shows **"Update available: build N. Tap to download"**. Tapping it downloads the new `Host.apk`; open it to
install over the old version. Settings shows your current build and has a "Check for updates" button.

This needs the repository to be **public**, because the app reads the releases without signing in.
(Repo Settings > General > Danger Zone > Change visibility.) With a private repo, updates still build;
you just download them from the Releases page yourself.

## Working with Claude Code

`CLAUDE.md` tells Claude Code how this project works. Open Claude Code in this folder, describe a change,
and it edits `www/index.html`, tests it with `tools/smoke.py`, commits and pushes. A few minutes later the
update shows up in the app.

## Notes

- This is a debug build, signed with a development key. It's fine for your own phone,
  but the Play Store needs a release build with your own signing key.
- The font loads from Google Fonts when you're online. Offline, the game uses your phone's
  system font and plays the same.
- App name, ID, and splash color live in `capacitor.config.json`.
  The full-screen behavior lives in `android/app/src/main/java/com/hostgame/app/MainActivity.java`.
