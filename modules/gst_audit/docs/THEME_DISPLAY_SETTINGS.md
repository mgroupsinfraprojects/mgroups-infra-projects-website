# Theme & Display Settings

## Purpose

The desktop software includes a dedicated **Settings** tab for interface customization.

## Supported settings

| Setting | Options |
|---|---|
| Theme | Professional Light, Professional Dark, Professional Blue, Audit High Contrast |
| Font size | 8–18 pt |
| Display density | Compact, Comfortable, Large |
| Window size | 1280x800, 1320x820, 1440x900, 1600x950, 1920x1080, Fullscreen |

## Professional recommendation

- **Professional Light**: normal office/accounting use.
- **Professional Dark**: long working sessions.
- **Professional Blue**: polished corporate style.
- **Audit High Contrast**: review-heavy work where warnings and row details must be easy to read.

## Technical design

Settings are saved locally through `QSettings`, so the app remembers the selected theme, font size, density, and window size after reopening.

Theme rendering is handled by:

```text
app/ui/theme_manager.py
```

The UI tab is built inside:

```text
app/ui/main_window.py
```

## Non-audit impact

Theme/display changes do not affect invoice processing, audit results, exported reports, or raw data.
They only affect the visual interface.
