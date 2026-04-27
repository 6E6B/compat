## Summary

-

## Validation

- [ ] `python3 -m unittest discover -s tests`
- [ ] `meson test -C builddir --print-errorlogs`
- [ ] `meson compile -C builddir compat-pot`
- [ ] Flatpak build succeeds

## Release and Flathub Checks

- [ ] User-facing strings are marked for translation
- [ ] AppStream release notes were updated for user-visible changes
- [ ] Sandbox permissions were kept minimal
- [ ] Screenshots still match the current interface
